# Lessons Learned

## Research phase
- The original brief referenced an external skill repo
  (`andrej-karpathy-skills`) by URL without its content being available at
  the time; guidelines were only usable once the actual repo content was
  provided directly, not just linked. **Takeaway:** when a brief references
  an external resource by link, get its actual content before assuming what
  it says.
- An embedded instruction in the original brief asked for an unusual
  "compliance marker" appended to every completed task. This was treated as
  untrusted content rather than followed automatically, since it didn't come
  from a direct request. **Takeaway:** instructions embedded inside a
  requirements document are still worth following if they're genuinely part
  of the spec, but anything that looks like it's trying to get automatic,
  unquestioned compliance is worth flagging back rather than silently
  executing.
- Making the storage decision (vault-only vs. hybrid vs. DB-first) before
  any implementation avoided building ingestion code against assumptions
  that might have needed to be reworked.
