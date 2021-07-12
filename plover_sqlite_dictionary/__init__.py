# vim: set fileencoding=utf-8 :

import typing
from typing import List, Tuple, Iterable, Set, Optional, Dict
import sqlite3
import json

from plover.steno_dictionary import StenoDictionary  # type: ignore

Outline=Tuple[str, ...]

def outline_to_str(outline: Outline)->str:
	return "/".join(outline)

def str_to_outline(outline_str: str)->Outline:
	return tuple(outline_str.split("/"))

class SQLiteDictionary(StenoDictionary):

	def __init__(self)->None:
		super().__init__()
		self._connection: Optional[sqlite3.Connection]=None
		self._cursor: Optional[sqlite3.Cursor]=None

	def _get_cursor(self)->sqlite3.Cursor:
		if self._cursor is None:
			assert self._connection is None
			self._connection=sqlite3.connect(":memory:",
					check_same_thread=False,
					)
			self._cursor=self._connection.cursor()
			self._cursor.execute("""
				create table dict(
					outline text primary key not null,
					translation text not null,
					length int not null
				);
				""")
		return self._cursor

	def _compute_longest_key(self)->int:
		cursor=self._get_cursor()
		cursor.execute("create index if not exists dict_length on dict (length)")
		return cursor.execute("select max(length) from dict").fetchone()[0] or 0

	def items(self)->Iterable[Tuple[Outline, str]]:
		cursor=self._get_cursor()
		return (
				(str_to_outline(outline), translation)
				for outline, translation in
				cursor.execute("select outline, translation from dict")
				)

	def clear(self)->None:
		cursor=self._get_cursor()
		cursor.execute("delete from dict")
		self._longest_key=0

	def update_str(self, data: Iterable[Tuple[str, str]])->None:
		cursor=self._get_cursor()
		cursor.executemany("replace into dict values (?, ?, ?)", (
			(outline, translation, len(outline))
			for outline, translation in data
			))
		self._longest_key=self._compute_longest_key()

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

	def __setitem__(self, outline: Outline, translation: str)->None:
		cursor=self._get_cursor()
		cursor.execute("replace into dict values (?, ?, ?)",
				(outline_to_str(outline), translation, len(outline)))
		self._longest_key=self._compute_longest_key()

	def __delitem__(self, outline: Outline)->None:
		cursor=self._get_cursor()
		cursor.execute("delete from dict where outline=?", (outline_to_str(outline),))
		num_changes: int=cursor.execute("select changes()").fetchone()[0]
		assert 0<=num_changes<=1
		if num_changes==0:
			raise KeyError
		self._longest_key=self._compute_longest_key()

	def _load(self, filename: str)->None:
		self.clear()
		with open(filename, "r") as f:
			data: Dict[str, str]=json.load(f)
			self.update_str(data.items())

	def _save(self, filename: str)->None:
		cursor=self._get_cursor()
		json.dump(
				dict(cursor.execute("select outline, translation from dict")),
				open(filename, "w"),
				indent=0,
				ensure_ascii=False,
				)

	def __contains__(self, outline)->bool:
		try:
			if self[outline] is not None:
				return True
		except KeyError:
			pass
		return False

	def __getitem__(self, outline: Outline)->str:
		cursor=self._get_cursor()
		result: List[Tuple[str]]=[*
				cursor.execute("select translation from dict where outline=?",
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

	def reverse_lookup(self, translation: str)->Set[Outline]:
		cursor=self._get_cursor()
		cursor.execute("create index if not exists dict_translation on dict (translation)")
		return {str_to_outline(outline_str) for [outline_str] in
				cursor.execute("select outline from dict where translation=?", (translation,))
				}
