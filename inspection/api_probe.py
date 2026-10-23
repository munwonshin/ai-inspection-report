"""Explicit synthetic connectivity check; never reads documents or writes reports."""
def main():
    import sys,json,time,ssl,urllib.request
    from pathlib import Path
    from . import api,vault
    target=Path(sys.argv[2])
    # Reserve the explicit diagnostic output first. Never overwrite another file.
    with target.open('x',encoding='utf-8') as output:
        result={'model':api.MODEL,'proxy_configured':bool(urllib.request.getproxies()),'tls':ssl.OPENSSL_VERSION}
        started=time.monotonic()
        try:
            context=ssl.create_default_context()
            result['ca_certificates']=context.cert_store_stats().get('x509_ca',0)
            result['certificate_required']=context.verify_mode==ssl.CERT_REQUIRED
            result['hostname_checked']=context.check_hostname
            key=vault.read();result['stored_key']=bool(key)
            if key:
                usage=api.connection(key)
                result.update(ok=True,total_tokens=usage.get('total_tokens'))
            else:result.update(ok=False,category='missing_key')
        except api.ApiFailure as e:
            result.update(ok=False,category=e.kind,safe_error=str(e))
        except Exception as e:
            result.update(ok=False,category='local_runtime',error_type=type(e).__name__)
        result['elapsed_seconds']=round(time.monotonic()-started,3)
        json.dump(result,output,ensure_ascii=False,indent=2)
