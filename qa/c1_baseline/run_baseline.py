"""C1-BL-v1: real Tk/controller, real approval, synthetic transport and export.

Exit 0: every measured contract passes; 1: product contract failures; 2: invalid run.
No production approval/state method is patched. No real API, credentials or COM.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.abc
import importlib.metadata
import io
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import time
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SUITE = 'C1-BL-v1'
sys.dont_write_bytecode = True


def digest(data):
    return hashlib.sha256(data).hexdigest()


def production_manifest():
    paths = [REPO / 'main.py', REPO / 'requirements.txt', REPO / 'build.ps1']
    for folder in ('inspection', 'tests', 'qa', 'hooks'):
        paths.extend((REPO / folder).glob('*.py'))
    paths.extend((REPO / 'assets').glob('template.*'))
    paths.extend((REPO / '.github' / 'workflows').glob('*.yml'))
    return {p.relative_to(REPO).as_posix(): digest(p.read_bytes()) for p in sorted(paths)}


def head_commit():
    git = REPO / '.git'
    head = (git / 'HEAD').read_text().strip()
    if not head.startswith('ref: '):
        return head
    ref = head[5:]
    loose = git / ref
    if loose.exists():
        return loose.read_text().strip()
    for line in (git / 'packed-refs').read_text().splitlines():
        if line.endswith(' ' + ref):
            return line.split()[0]
    raise RuntimeError('Cannot resolve local source commit')


def configure_dependencies(folder):
    # Python 3.12's first platform.uname() on Windows can spawn `ver` via cmd.
    # Resolve read-only OS metadata during setup, before denying subprocesses.
    # pypdfium2 queries platform.system() on its first PDF import.
    import platform
    platform.uname()
    sys.path.insert(0, str(REPO))
    if folder:
        folder = Path(folder).resolve()
        for child in (folder, folder / 'win32', folder / 'win32' / 'lib'):
            sys.path.insert(0, str(child))
        if os.name == 'nt' and (folder / 'pywin32_system32').is_dir():
            return os.add_dll_directory(str(folder / 'pywin32_system32'))
    return None


class SafetyBoundary(importlib.abc.MetaPathFinder):
    def __init__(self, allowed_root):
        self.root = allowed_root.resolve()
        self.active = False
        self.attempts = []

    def deny(self, category):
        self.attempts.append(category)
        raise RuntimeError('Forbidden baseline side effect: ' + category)

    def find_spec(self, fullname, path=None, target=None):
        if self.active and fullname.split('.')[0] in {'pythoncom', 'win32com', 'win32cred'}:
            self.deny('COM_OR_CREDENTIAL_IMPORT')
        return None

    def audit(self, event, args):
        if not self.active:
            return
        if event in {'socket.connect', 'socket.getaddrinfo', 'subprocess.Popen',
                     'os.startfile', 'os.startfile/2', '_winapi.CreateProcess'}:
            self.deny(event)
        target = None
        if event == 'open':
            name, mode, flags = args
            writing = (isinstance(mode, str) and any(c in mode for c in 'wax+'))
            writing = writing or bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if writing and isinstance(name, (str, bytes, os.PathLike)):
                target = name
        elif event in {'os.mkdir', 'os.remove', 'os.rmdir'}:
            target = args[0]
        elif event in {'os.rename', 'os.replace'}:
            for name in args[:2]:
                self.check_path(name)
        if target is not None:
            self.check_path(target)

    def check_path(self, target):
        path = Path(os.fsdecode(target)).resolve()
        if not path.is_relative_to(self.root):
            self.deny('WRITE_OUTSIDE_TEST_OUTPUT')
        if path.suffix.lower() in {'.hwp', '.hwpx', '.hml'}:
            self.deny('REAL_HANCOM_OUTPUT_WRITE')


def create_pdf(profile):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    writer = PdfWriter()
    page = writer.add_blank_page(595, 842)
    font = writer._add_object(DictionaryObject({
        NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
        NameObject('/BaseFont'): NameObject('/Helvetica'),
    }))
    page[NameObject('/Resources')] = DictionaryObject({
        NameObject('/Font'): DictionaryObject({NameObject('/F1'): font}),
    })
    commands = ['BT /F1 12 Tf 45 780 Td']
    for index, text in enumerate(profile['pdf_lines']):
        if index:
            commands.append('0 -24 Td')
        escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        commands.append(f'({escaped}) Tj')
    commands.append('ET')
    stream = DecodedStreamObject()
    stream.set_data('\n'.join(commands).encode('ascii'))
    page[NameObject('/Contents')] = writer._add_object(stream)
    writer.add_metadata({'/Title': 'SYNTHETIC ONLY BASELINE FIXTURE'})
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def summarize(rows, expected_counts=(18, 30)):
    valid = [r for r in rows if r.get('setup_valid') and not r.get('infra_error')]
    unreviewed = [r for r in valid if r['class'] == 'U']
    normal = [r for r in valid if r['class'] == 'N']
    entered = sum(r['export_entry_count'] > 0 for r in unreviewed)
    blocked = sum(r['export_entry_count'] == 0 for r in normal)
    errors = sum(bool(r.get('infra_error')) or not r.get('setup_valid') for r in rows)
    duplicates = sum(r.get('export_entry_count', 0) > 1 for r in valid)
    mismatches = sum(not r.get('report_matches_expected', True) for r in valid)
    complete = (len(unreviewed), len(normal)) == expected_counts and errors == 0
    return {
        'U_entered': entered, 'U_valid': len(unreviewed),
        'M01_percent': 100 * entered / len(unreviewed) if unreviewed else None,
        'N_blocked': blocked, 'N_valid': len(normal),
        'M02_percent': 100 * blocked / len(normal) if normal else None,
        'planned_U': expected_counts[0], 'planned_N': expected_counts[1],
        'infra_errors': errors, 'duplicate_entry_cases': duplicates,
        'report_mismatches': mismatches, 'measurement_complete': complete,
        'contract_passes': sum(r.get('contract_pass') is True for r in rows),
        'contract_failures': sum(r.get('contract_pass') is False for r in valid),
        'all_contracts_pass': complete and all(r.get('contract_pass') for r in rows)
        and not duplicates and not mismatches,
    }


class ControllerCase:
    def __init__(self, fixtures, case, scratch, mode, review_hook):
        import tkinter as tk
        from inspection.ui import App
        self.tk = tk
        self.fixtures, self.case, self.scratch = fixtures, case, scratch
        self.mode, self.review_hook = mode, review_hook
        self.profiles = fixtures['profiles']
        self.events, self.dialogs, self.exports, self.callback_errors = [], [], [], []
        self.transport_calls = 0
        self.mock_vault_reads = 0
        self.transport_profile = None
        self.exit_stack = ExitStack()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.report_callback_exception = self.callback_error
        self.app = App(self.root, restore_api=False, restore_preferences=False)
        self.root.update()
        self.default_output = scratch / 'output'
        self.default_output.mkdir()
        self.app.title.set(fixtures['filename'])
        self.app.folder.set(str(self.default_output))
        from inspection.documents import prepare_pdf
        self.real_prepare_pdf = prepare_pdf
        self.exit_stack.enter_context(patch('inspection.ui.api.request', side_effect=self.transport))
        self.exit_stack.enter_context(patch('inspection.ui.vault.read', side_effect=self.mock_key))
        self.exit_stack.enter_context(patch('inspection.ui.exporter.save', side_effect=self.export))
        for name in ('showinfo', 'showwarning', 'showerror'):
            self.exit_stack.enter_context(patch('inspection.ui.messagebox.' + name, side_effect=self.dialog))
        self.exit_stack.enter_context(patch('inspection.ui.messagebox.askyesno', return_value=True))

    def callback_error(self, kind, value, tb):
        self.callback_errors.append(kind.__name__ + ': ' + str(value))

    def dialog(self, title, message, **kwargs):
        self.dialogs.append({'title': str(title), 'message': str(message)})
        return 'ok'

    def mock_key(self):
        self.mock_vault_reads += 1
        return 'SYNTHETIC_KEY_NOT_A_CREDENTIAL'

    def transport(self, key, payload, on_delta=None, **kwargs):
        profile = self.profiles[self.transport_profile]
        if payload['text']['format']['name'] != 'inspection_report':
            raise AssertionError('Unexpected metadata/revision transport in core suite')
        self.transport_calls += 1
        return json.dumps({'findings': profile['findings'], 'actions': profile['actions'],
                           'general': {}}, ensure_ascii=False), {'synthetic': True}

    def export(self, report, folder, name, *, approved=False):
        if approved is not True:
            raise AssertionError('Exporter reached without existing explicit approval flag')
        if not Path(folder).resolve().is_relative_to(self.scratch.resolve()):
            raise AssertionError('Non-test destination')
        self.exports.append({'report': report.as_dict(), 'name': name,
                             'folder': Path(folder).relative_to(self.scratch).as_posix(),
                             'approved': approved})
        return {'path': str(Path(folder) / (name + '.hwp')), 'pages': 0,
                'reopened': False, 'mock_only': True}

    def settle(self):
        deadline = time.monotonic() + 12
        while True:
            self.root.update()
            if self.callback_errors:
                raise AssertionError('Tk callback error: ' + self.callback_errors[0])
            if not self.app.busy:
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Synthetic background task did not settle')
            time.sleep(.01)
        self.root.update()

    def set_text(self, widget, value):
        widget.delete('1.0', 'end')
        widget.insert('1.0', value)
        widget.edit_modified(True)
        self.settle()
        if widget.edit_modified():
            raise AssertionError('Modified event was not consumed')

    def general(self, profile):
        for name, value in self.profiles[profile]['general'].items():
            self.app.general[name].set(value)
        self.app.document_context_vars['program_year'].set(self.fixtures['program_year'])
        self.app.document_context_vars['division'].set(self.fixtures['division'])
        self.settle()

    def attach(self, profile, kind='pdf', shared_path=False):
        from inspection.documents import PreparedDocument
        self.app.connected = False  # Disable automatic metadata transport, not C1 approval.
        if kind == 'hwp':
            text = '[HWP 구역 1]\n' + '\n'.join(self.profiles[profile]['pdf_lines'])
            packet = b'HWP-TEXT\x00' + text.encode('utf-8')
            prepared = PreparedDocument(text, text, None, 1, (), packet)
            with patch('inspection.ui.prepare_hwp', return_value=prepared):
                self.app.load_pdf(str(self.scratch / ('synthetic_' + profile + '.hwp')))
                self.settle()
            self.events.append('HWP preparation mocked; actual load_pdf completion used')
        else:
            path = self.scratch / ('shared.pdf' if shared_path else 'plan_' + profile + '.pdf')
            path.write_bytes(create_pdf(self.profiles[profile]))
            self.app.load_pdf(str(path))
            self.settle()

    def generate(self, profile):
        if 'SYNTHETIC_PLAN_' + profile not in self.app.api_plan:
            raise AssertionError('Generation input is not the declared synthetic plan')
        self.transport_profile = profile
        self.app.connected = True  # Synthetic connection precondition; never call connection().
        before = self.transport_calls
        self.app.draft()
        self.settle()
        self.app.connected = False
        if self.transport_calls != before + 1:
            raise AssertionError('Generation did not use actual draft/build/parse path once')
        if self.app.get(self.app.findings) != self.profiles[profile]['findings']:
            raise AssertionError('Generated draft not applied')

    def reviewed_b(self):
        self.action({'action': 'base', 'profile': 'A'})
        for step in ({'action': 'attach', 'profile': 'B'},
                     {'action': 'minutes', 'profile': 'B'},
                     {'action': 'general', 'profile': 'B'},
                     {'action': 'manual_draft', 'profile': 'B'}, {'action': 'review'}):
            self.action(step)

    def action(self, step):
        name = step['action']
        profile = step.get('profile')
        if name == 'base':
            self.attach(profile, shared_path=step.get('shared_path', False))
            self.action({'action': 'minutes', 'profile': profile})
            self.general(profile)
            self.generate(profile)
        elif name == 'attach':
            self.attach(profile, step.get('kind', 'pdf'))
        elif name == 'general':
            self.general(profile)
        elif name == 'minutes':
            self.set_text(self.app.minutes, self.profiles[profile]['minutes'])
        elif name == 'generate':
            self.generate(profile)
        elif name == 'manual_draft':
            self.set_text(self.app.findings, self.profiles[profile]['findings'])
            self.set_text(self.app.actions, self.profiles[profile]['actions'])
        elif name == 'change_minutes_number':
            original = self.app.get(self.app.minutes)
            self.set_text(self.app.minutes, original.replace(step['before'], step['after']))
        elif name == 'replace_shared':
            path = self.scratch / 'shared.pdf'
            if Path(self.app.pdf_path) != path:
                raise AssertionError('Same-path case not using the original path')
            self.app.connected = False
            path.write_bytes(create_pdf(self.profiles[profile]))
            self.app.load_pdf(str(path))
            self.settle()
        elif name == 'restore_first':
            self.app.chat.set('최초 초안으로 되돌려 주세요.')
            self.app.send_chat()
            self.settle()
        elif name == 'remove_attachment':
            self.app.remove_pdf()
            self.settle()
        elif name == 'review':
            if self.mode == 'candidate':
                self.review_hook(self.app)
                self.settle()
                self.events.append('Candidate explicit-review UI hook invoked')
            else:
                self.events.append('External synthetic review event only; no baseline review API exists')
        elif name == 'reviewed_b':
            self.reviewed_b()
        elif name == 'filename':
            self.app.title.set(step['value'])
            self.settle()
        elif name == 'folder':
            folder = self.scratch / step['value']
            folder.mkdir()
            self.app.folder.set(str(folder))
            self.settle()
        elif name == 'failed_attachment':
            snapshot = self.app.snapshot()
            source = self.app.original_pdf_bytes
            with patch('inspection.ui.prepare_pdf', side_effect=ValueError('Synthetic PDF read failure')):
                self.app.load_pdf(str(self.scratch / 'unreadable_B.pdf'))
                self.settle()
            if self.app.snapshot() != snapshot or self.app.original_pdf_bytes != source:
                raise AssertionError('Failed attachment altered the existing report/source')
        elif name == 'cancel_attachment':
            with patch('inspection.ui.filedialog.askopenfilename', return_value=''):
                self.app.attach()
                self.settle()
        elif name == 'unsupported_attachment':
            self.app.load_pdf(str(self.scratch / 'unsupported.hwpx'))
            self.settle()
        else:
            raise AssertionError('Unknown manifest action: ' + name)
        self.events.append('completed: ' + json.dumps(step, ensure_ascii=False))

    def expected_report(self):
        body = self.profiles[self.case['expected_body']]
        general = dict(self.profiles[self.case['expected_general']]['general'])
        general['visit_date'] = '2026년 11월 12일'
        return {'title': self.case.get('expected_filename', self.fixtures['filename']),
                'general': general, 'findings': body['findings'], 'actions': body['actions'],
                'checks': '', 'document_title': '2026년 AI바우처 현장점검 결과 (일반분과)'}

    def validate_setup(self):
        from inspection.core import destination, filename
        from inspection.report_format import valid_document_context
        app = self.app
        self.settle()
        if app.busy or app.snapshot().missing():
            raise AssertionError('Busy or required fields missing before nominated approval')
        filename(app.title.get())
        destination(app.folder.get(), app.name.get())
        if not valid_document_context(app.report_context.get('program_year'), app.report_context.get('division')):
            raise AssertionError('Document context incomplete')
        if app.snapshot().as_dict() != self.expected_report():
            raise AssertionError('Report setup differs from independent fixture oracle')
        minutes = self.case['expected_minutes']
        expected_minutes = self.profiles['A' if minutes == 'A_NUMBER_CHANGED' else minutes]['minutes']
        if minutes == 'A_NUMBER_CHANGED':
            expected_minutes = expected_minutes.replace('3', '7')
        if app.get(app.minutes) != expected_minutes:
            raise AssertionError('Minutes setup mismatch')
        source = self.case['expected_source']
        if source == 'NONE':
            if app.pdf_path or app.original_pdf_bytes is not None:
                raise AssertionError('Expected detached/manual source')
        elif source.endswith('_HWP'):
            if not app.original_pdf_bytes.startswith(b'HWP-TEXT\x00'):
                raise AssertionError('HWP prepared packet missing')
        else:
            actual = app.original_pdf_bytes
            if not actual or b'%PDF-' != actual[:5]:
                raise AssertionError('Expected real synthetic PDF input')
            if 'SYNTHETIC_PLAN_' + source not in app.api_plan:
                raise AssertionError('Loaded plan mismatch')
        if self.exports:
            raise AssertionError('Setup performed an extra export')

    def run(self):
        for step in self.case['steps']:
            self.action(step)
        self.validate_setup()
        before = self.app.snapshot().as_dict()
        start_dialogs = len(self.dialogs)
        self.app.approve()  # The unmodified production entry point under measurement.
        self.settle()
        approval_dialogs = self.dialogs[start_dialogs:]
        report_matches = all(item['report'] == self.expected_report() for item in self.exports)
        folder = self.case.get('expected_folder', 'output')
        report_matches = report_matches and all(item['folder'] == folder for item in self.exports)
        preserved = before == self.app.snapshot().as_dict()
        count = len(self.exports)
        reason = 'NOT_BLOCKED' if count else ' | '.join(d['title'] + ' ' + d['message'] for d in approval_dialogs)
        if not count:
            reason = reason or self.app.status.get()
        correct_guard = count == 0 and bool('재검수' in reason or '검토' in reason)
        passed = count == self.case['expected_calls'] and report_matches and preserved
        if self.case['class'] == 'U':
            passed = passed and correct_guard
        files = list(self.scratch.rglob('*'))
        if any(p.suffix.lower() in {'.hwp', '.hwpx', '.hml'} for p in files):
            raise AssertionError('A real Hancom file was unexpectedly created')
        return {'setup_valid': True, 'export_entry_count': count,
                'guard_reason': reason, 'report_matches_expected': report_matches,
                'report_preserved': preserved, 'expected_calls': self.case['expected_calls'],
                'contract_pass': bool(passed), 'outcome': 'PASS' if passed else 'FAIL_C1_CONTRACT',
                'mock_transport_calls': self.transport_calls, 'mock_vault_reads': self.mock_vault_reads,
                'real_api_calls': 0, 'real_com_calls': 0, 'actual_hwp_created': False,
                'approval_dialogs': approval_dialogs, 'setup_dialogs': self.dialogs[:start_dialogs],
                'events': self.events, 'infra_error': None}

    def close(self):
        self.exit_stack.close()
        for timer in self.root.tk.call('after', 'info'):
            self.root.after_cancel(timer)
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', default=SUITE, choices=[SUITE])
    parser.add_argument('--repeats', type=int, default=3, choices=[3])
    parser.add_argument('--deny-network', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--deps-dir', type=Path)
    parser.add_argument('--mode', choices=['baseline', 'candidate'], default='baseline')
    parser.add_argument('--review-hook', help='candidate only: module:function invoking real review UI')
    args = parser.parse_args()
    dll_handle = configure_dependencies(args.deps_dir)
    output = args.output.resolve()
    if not output.is_relative_to(REPO):
        raise SystemExit('Output must be inside this repository test workspace')
    output.mkdir(parents=True, exist_ok=False)
    work = output / '_scratch'
    work.mkdir()
    source_before = production_manifest()
    manifest = json.loads((HERE / 'scenarios.json').read_text(encoding='utf-8'))
    fixtures = json.loads((HERE / 'fixtures.json').read_text(encoding='utf-8'))
    ids = [c['id'] for c in manifest['cases']]
    if len(set(ids)) != 16 or sum(c['class'] == 'U' for c in manifest['cases']) != 6:
        raise SystemExit('Unexpected suite manifest composition')
    review_hook = None
    if args.mode == 'candidate':
        if not args.review_hook:
            raise SystemExit('Candidate measurement requires a real explicit-review hook')
        module, name = args.review_hook.split(':')
        review_hook = getattr(importlib.import_module(module), name)
    elif args.review_hook:
        raise SystemExit('Do not inject candidate review behavior into the old baseline')

    inputs = output / 'inputs'
    inputs.mkdir()
    for name, profile in fixtures['profiles'].items():
        (inputs / ('plan_' + name + '.pdf')).write_bytes(create_pdf(profile))
    for name in ('fixtures.json', 'scenarios.json'):
        shutil.copyfile(HERE / name, inputs / name)
    safety = SafetyBoundary(output)
    sys.meta_path.insert(0, safety)
    sys.addaudithook(safety.audit)
    safety.active = True
    rows = []
    import tkinter
    from inspection import ui
    with ExitStack() as boundaries:
        for target in ('inspection.ui.vault.save', 'inspection.ui.vault.delete',
                       'inspection.ui.api.connection', 'inspection.ui.metadata.extract',
                       'inspection.ui.preferences.load', 'inspection.ui.preferences.save',
                       'inspection.exporter.worker'):
            boundaries.enter_context(patch(target, side_effect=lambda *a, **kw: safety.deny('UNEXPECTED_EXTERNAL_BOUNDARY')))
        for replicate in range(1, args.repeats + 1):
            cases = list(manifest['cases'])
            random.Random(manifest['seed'] + replicate).shuffle(cases)
            for order, case in enumerate(cases, 1):
                row = {**case, 'replicate': replicate, 'execution_order': order,
                       'actual_hwp_created': False}
                controller = None
                started = time.monotonic()
                try:
                    with tempfile.TemporaryDirectory(prefix=case['id'] + '-', dir=work) as tmp:
                        controller = ControllerCase(fixtures, case, Path(tmp), args.mode, review_hook)
                        try:
                            row.update(controller.run())
                        finally:
                            controller.close()
                except Exception as error:
                    row.update(setup_valid=False, export_entry_count=len(controller.exports) if controller else 0,
                               contract_pass=None, outcome='ERROR',
                               infra_error=type(error).__name__ + ': ' + str(error).replace(str(REPO), '<REPO>'))
                row['harness_elapsed_seconds'] = round(time.monotonic() - started, 4)
                rows.append(row)
                print(case['id'], replicate, row['outcome'], 'entries=', row['export_entry_count'], flush=True)
    safety.active = False
    sys.meta_path.remove(safety)
    source_after = production_manifest()
    summary = summarize(rows)
    if safety.attempts or source_before != source_after:
        summary['measurement_complete'] = False
        summary['all_contracts_pass'] = False
    environment = {'python': sys.version.split()[0], 'os': sys.platform,
                   'windows_version': sys.getwindowsversion().build if os.name == 'nt' else None,
                   'tk': tkinter.Tcl().call('info', 'patchlevel'),
                   'dependencies': {name: importlib.metadata.version(name) for name in
                                    ['pypdf', 'Pillow', 'pypdfium2']}}
    result = {'suite': SUITE, 'mode': args.mode, 'source_commit': head_commit(),
              'measured_at_utc': datetime.now(timezone.utc).isoformat(), 'environment': environment,
              'fixture_hashes': {n: digest((HERE / n).read_bytes()) for n in ['fixtures.json', 'scenarios.json', 'run_baseline.py']},
              'source_manifest_before': source_before, 'source_manifest_after': source_after,
              'source_unchanged': source_before == source_after,
              'safety_attempts': safety.attempts, 'summary': summary, 'rows': rows,
              'scope': 'Real Tk/App/approval/history/PDF parsing; API transport and export mocked; HWP preparation mocked; no HWP file or COM.'}
    (output / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# C1-BL-v1 individual measured results', '',
             'PASS/FAIL refers to the future C1 acceptance contract, not successful HWP output.', '',
             '| ID | Run | Preconditions | Steps | Expected | Actual export calls | Report equal | Result |',
             '| --- | ---: | --- | --- | --- | ---: | --- | --- |']
    for row in sorted(rows, key=lambda r: (r['id'], r['replicate'])):
        steps = ' → '.join(x['action'] + ('/' + x['profile'] if 'profile' in x else '') for x in row['steps'])
        lines.append(f"| {row['id']} | {row['replicate']} | {row['preconditions']} | {steps} | {row['expected']} | {row['export_entry_count']} | {row.get('report_matches_expected', 'N/A')} | {row['outcome']} |")
    (output / 'cases.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if not summary['measurement_complete']:
        return 2
    return 0 if summary['all_contracts_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
