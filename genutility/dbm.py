
def dbm_items(db):
	for key in db:
		value = db[key]
		yield key, value
