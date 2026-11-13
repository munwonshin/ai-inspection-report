"""In-memory source/review binding; no document logging or persistent state."""
import hashlib
import json


def prepared_identity(document):
    """Identify the complete processed input, not the filesystem path."""
    fields = (document.local_text, document.api_text, document.original_bytes,
              document.visual_pdf, document.page_count, document.visual_pages)
    digest = hashlib.sha256()
    for value in fields:
        if isinstance(value, bytes):
            data = value
        else:
            data = json.dumps(value, ensure_ascii=False, sort_keys=True,
                              separators=(',', ':')).encode('utf-8')
        digest.update(len(data).to_bytes(8, 'big'))
        digest.update(data)
    return digest.hexdigest()


class ReviewState:
    def __init__(self):
        self.workspace = 0
        self.source_generation = 0
        self.content_generation = 0
        self.source = None
        self.content = None
        self.permit = None
        self.kind = 'REVIEW_REQUIRED'
        self.reason = '현재 자료와 본문·일반현황을 대조해 재검수해 주세요.'

    def observe(self, attachment, minutes, report):
        source = (attachment, minutes.replace('\r\n', '\n').replace('\r', '\n'))
        content = (tuple(sorted(report.general)), report.findings,
                   report.actions, report.checks, report.document_title)
        source_changed = source != self.source
        content_changed = content != self.content
        if source_changed:
            self.source_generation += 1
            self.source = source
        if content_changed:
            self.content_generation += 1
            self.content = content
        if source_changed or content_changed:
            reason = ('자료가 변경되어 기존 초안 재검수가 필요합니다.' if source_changed
                      else '본문·일반현황이 변경되어 재검수가 필요합니다.')
            self.require_review(reason)

    @property
    def token(self):
        return self.workspace, self.source_generation, self.content_generation

    @property
    def source_id(self):
        return hashlib.sha256(repr(self.source).encode('utf-8')).hexdigest()

    @property
    def allowed(self):
        return self.permit == self.token

    def require_review(self, reason):
        self.permit = None
        self.kind = 'REVIEW_REQUIRED'
        self.reason = reason

    def invalidate(self, reason):
        # An explicit restore is a new editing event even with identical text.
        self.content_generation += 1
        self.require_review(reason)

    def accept(self, kind):
        self.permit = self.token
        self.kind = kind

    def reset(self):
        self.workspace += 1
        self.source = None
        self.content = None
        self.require_review('새 작업의 자료·본문·일반현황을 재검수해 주세요.')
