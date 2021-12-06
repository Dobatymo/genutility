from __future__ import generator_stop

from typing import Any, Hashable, List

from unqlite import UnQLite


def query_by_field_eq(db: UnQLite, col: str, key: Hashable, value: Any) -> List[dict]:
    script = """
        $zCallback = function($doc) {
            return $doc[$key] == $value;
        };

        $data = db_fetch_all($col, $zCallback);
    """

    with db.vm(script) as vm:
        vm["col"] = col
        vm["key"] = key
        vm["value"] = value
        vm.execute()
        return vm["data"]


def query_by_field_intersect(db: UnQLite, col: str, key: Hashable, value: List[Any]) -> List[dict]:
    script = """
        $zCallback = function($doc) {
            return count(array_intersect($doc[$key], $value)) > 0;
        };

        $data = db_fetch_all($col, $zCallback);
    """

    with db.vm(script) as vm:
        vm["col"] = col
        vm["key"] = key
        vm["value"] = value
        vm.execute()
        return vm["data"]
