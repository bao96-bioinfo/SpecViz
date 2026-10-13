from exporter import export_rows


def save_export(storage, owner, caller, rows, password=None):
    exported = export_rows(owner, caller, rows, password)
    return storage.save(exported)
