# plover-sqlite-dictionary
SQLite-based dictionary format for Plover. Consumes less memory for large dictionaries.

### Why?

* Reduce memory (RAM) consumption.  (however, the word list for orthography
  suffix rules and Qt modules still take a considerable amount of RAM)
* Faster loading/startup speed.

### Note

The SQL dictionary format is not completely compatible with Plover's API specification,
the plugin may fail to work properly in future Plover versions.

### Usage

There are two possible file formats:

* SQLite-based: `.sql` extension.

   Use the "New dictionary" feature in Plover to create one, or "Save dictionary as..." feature
   to convert from other dictionary formats.

   **Note**:

   * If there's a table named `readonly` (the content doesn't matter), the dictionary will be
   considered read-only.

   Because of [a Plover bug](https://github.com/openstenoproject/plover/issues/1399), modifying the
   dictionary file and reloading the dictionary in Plover might not update the read-only status.

   * The file size is larger than the size of a JSON dictionary.
   * When an entry in the file on the disk is changed, it's automatically updated into Plover.
   * When the dictionary is deleted on disk, attempt to modify the dictionary in Plover
   will cause "attempt to write a readonly database" error; otherwise, the dictionary remains usable.
   * It's possible to have additional columns for auxiliary entries, as long as the dictionary is read-only.

* JSON: stored as plain JSON file on disk. `.jssql` extension.

   Note: This format takes longer to load than normal JSON dictionary.

   Can be used like a normal Plover dictionary.
