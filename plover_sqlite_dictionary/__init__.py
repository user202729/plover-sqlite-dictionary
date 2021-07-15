# vim: set fileencoding=utf-8 :

import typing
from typing import List, Tuple, Iterable, Set, Optional, Dict, TypeVar, Callable, Any
import sqlite3
import json
import functools
import threading

from plover.steno_dictionary import StenoDictionary  # type: ignore

Outline=Tuple[str, ...]

def outline_to_str(outline: Outline)->str:
	return "/".join(outline)

def str_to_outline(outline_str: str)->Outline:
	return tuple(outline_str.split("/"))

F=TypeVar("F", bound=Callable)
def with_lock(f: F)->F:
	@functools.wraps(f)
	def wrap(self, *args, **kwargs)->Any:
		result=self._lock.acquire(timeout=1)
		assert result
		try:
			return f(self, *args, **kwargs)
		finally:
			self._lock.release()
	return typing.cast(F, wrap)


class SQLiteDictionaryBase(StenoDictionary):
	def __init__(self)->None:
		super().__init__()
		self._lock=threading.Lock()  # use this whenever connection is accessed.
		self._connection: Optional[sqlite3.Connection]=None
		self._connection_path: str=""
		self._cursor_value: Optional[sqlite3.Cursor]=None

	def _connect_unlocked(self, filename: str=":memory:")->None:
		if self._connection is not None and self._connection_path==filename:
			return
		self._connection=sqlite3.connect(filename, check_same_thread=False)
		self._connection_path=filename
		self._cursor_value=self._connection.cursor()
		self._cursor_value.execute("""
			create table if not exists dict(
				outline text primary key not null,
				translation text not null,
				length int not null
			);
			""")

	@with_lock
	def _connect(self, filename: str=":memory:")->None:
		self._connect_unlocked(filename)

	def _commit_unlocked(self)->None:
		assert self._connection
		self._connection.commit()

	@with_lock
	def _commit(self)->None:
		self._commit_unlocked()

	@property
	def _cursor(self)->sqlite3.Cursor:
		assert self._cursor_value is not None, (self.path, self._connection_path)
		assert self._lock.locked()
		return self._cursor_value

	def _compute_longest_key_unlocked(self)->int:
		self._cursor.execute("create index if not exists dict_length on dict (length)")
		return self._cursor.execute("select max(length) from dict").fetchone()[0] or 0

	@with_lock
	def compute_longest_key(self)->int:
		return self._compute_longest_key_unlocked()

	@with_lock
	def items(self)->Iterable[Tuple[Outline, str]]:
		return (
				(str_to_outline(outline), translation)
				for outline, translation in
				self._cursor.execute("select outline, translation from dict")
				)

	def _clear_unlocked(self)->None:
		self._cursor.execute("delete from dict")
		self._longest_key=0

	@with_lock
	def clear(self)->None:
		self._clear_unlocked()

	@with_lock
	def update_str(self, data: Iterable[Tuple[str, str]])->None:
		self._cursor.executemany("replace into dict values (?, ?, ?)", (
			(outline, translation, len(outline))
			for outline, translation in data
			))
		self._longest_key=self._compute_longest_key_unlocked()

	def update(self, *args)->None:
		assert not self.readonly
		iterable_list: List[Iterable[Tuple[Outline, str]]] = [
			a.items() if isinstance(a, (dict, StenoDictionary))
			else a for a in args
		]

		self.update_str(
			(outline_to_str(outline), translation)
			for iterable in iterable_list
			for outline, translation in iterable
			)

	@with_lock
	def __setitem__(self, outline: Outline, translation: str)->None:
		self._cursor.execute("replace into dict values (?, ?, ?)",
				(outline_to_str(outline), translation, len(outline)))
		self._longest_key=self._compute_longest_key_unlocked()

	@with_lock
	def __delitem__(self, outline: Outline)->None:
		self._cursor.execute("delete from dict where outline=?", (outline_to_str(outline),))
		num_changes: int=self._cursor.execute("select changes()").fetchone()[0]
		assert 0<=num_changes<=1
		if num_changes==0:
			raise KeyError
		self._longest_key=self._compute_longest_key_unlocked()

	def __contains__(self, outline)->bool:
		try:
			if self[outline] is not None:
				return True
		except KeyError:
			pass
		return False

	@with_lock
	def __getitem__(self, outline: Outline)->str:
		result: List[Tuple[str]]=[*
				self._cursor.execute("select translation from dict where outline=?",
					(outline_to_str(outline),))
				]
		assert len(result)<=1
		if len(result)==1: return result[0][0]
		raise KeyError

	def get(self, outline: Outline, fallback: str=None)->Optional[str]:
		try:
			return self[outline]
		except KeyError:
			return fallback

	@with_lock
	def reverse_lookup(self, translation: str)->Set[Outline]:
		self._cursor.execute("create index if not exists dict_translation on dict (translation)")
		return {str_to_outline(outline_str) for [outline_str] in
				self._cursor.execute("select outline from dict where translation=?", (translation,))
				}


class SQLiteDictionary(SQLiteDictionaryBase):
	def _load(self, filename: str)->None:
		path_was_none=False
		if self.path is None:  # type: ignore
			path_was_none=True
			self.path=filename
		self._connect(filename)
		self._longest_key=self.compute_longest_key()
		if path_was_none:
			self.path=None  # type: ignore

	@property
	def _cursor(self)->sqlite3.Cursor:
		assert self._lock.locked()
		if not self._connection_path:
			self._connect_unlocked(self.path)
			# the imaginary dict in RAM is empty
			self._clear_unlocked()
		else:
			assert self._connection_path==self.path, (self._connection_path, self.path)
		assert self._cursor_value is not None
		return self._cursor_value

	@with_lock
	def save(self)->None:
		self._cursor
		assert self._connection is not None
		self._commit_unlocked()

	def _save(self)->None:
		raise NotImplementedError


class SQLiteJSONDictionary(SQLiteDictionaryBase):
	def __init__(self)->None:
		super().__init__()
		self._connect()

	def _load(self, filename: str)->None:
		self.clear()
		with open(filename, "r") as f:
			data: Dict[str, str]=json.load(f)
			self.update_str(data.items())

	@with_lock
	def _save(self, filename: str)->None:
		json.dump(
				dict(self._cursor.execute("select outline, translation from dict")),
				open(filename, "w"),
				indent=0,
				ensure_ascii=False,
				)
