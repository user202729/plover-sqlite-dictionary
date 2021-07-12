# plover-sqlite-dictionary
SQLite-based dictionary format for Plover. Consumes less memory for large dictionaries.

### Why?

* Reduce memory (RAM) consumption.  (however, the word list for orthography
  suffix rules and Qt modules still take a considerable amount of RAM)
* Faster loading/startup speed.

### Usage

There are two possible file formats:

* SQLite-based: `.sql` extension. (*not implemented*)

   Use the "New dictionary" feature in Plover to create one, or "Save dictionary as..." feature
   to convert from other dictionary formats.

* JSON: stored as plain JSON file on disk. `.jssql` extension.

   Note: This format takes longer to load than normal JSON dictionary.

   Can be used like a normal Plover dictionary.
