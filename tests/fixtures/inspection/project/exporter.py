def export_rows(owner, caller, rows, password=None):
    if owner != caller:
        raise PermissionError("Only the owner may export")
    return rows[:100]
