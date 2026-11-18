/*
 * Stitchcraft data configuration for the warehouse sample.
 * `mode: "local"` seeds and persists every record in this browser under
 * `stitchcraft:warehouse-ops:*`; the app keeps working from file:// with no
 * network. Point `url`/`anonKey` at a Supabase-compatible REST endpoint and
 * set `mode: "remote"` to read the board from that API instead.
 */
window.STITCHCRAFT_DB = { mode: "local", kind: "local", url: "", anonKey: "", tablePrefix: "stitchcraft" };
