"""Keys are stored only in the current Windows user's Credential Manager."""
TARGET='AIInspectionReport/OpenAI/v1'

def read():
    import pywintypes
    import win32cred
    try:
        blob=win32cred.CredRead(TARGET,win32cred.CRED_TYPE_GENERIC)['CredentialBlob']
    except pywintypes.error as e:
        if e.winerror==1168:return ''
        raise RuntimeError('Windows 자격 증명 저장소를 읽지 못했습니다.') from None
    return blob.decode('utf-16-le') if isinstance(blob,bytes) else blob

def save(key):
    import pywintypes
    import win32cred
    if not key.strip() or '\n' in key or '\r' in key or len(key)>2000:
        raise ValueError('올바른 API 키를 입력해 주세요.')
    win32cred.CredWrite({'Type':win32cred.CRED_TYPE_GENERIC,'TargetName':TARGET,
        'UserName':'OpenAI','CredentialBlob':key.strip(),
        'Persist':win32cred.CRED_PERSIST_LOCAL_MACHINE},0)

def delete():
    import pywintypes
    import win32cred
    try:win32cred.CredDelete(TARGET,win32cred.CRED_TYPE_GENERIC)
    except pywintypes.error as e:
        if e.winerror!=1168:raise RuntimeError('API 키를 삭제하지 못했습니다.') from None
