/* Stitchcraft front-end module: read a half-built local site folder.
   Text assets only; binary files are intentionally skipped so the API payload
   stays small and the generator's file contract remains safe. */
(function () {
  'use strict';

  var ALLOWED = ['.html', '.css', '.js', '.json', '.svg', '.txt', '.md', '.webmanifest', '.xml'];
  var SKIP_PARTS = ['.git', 'node_modules', '__pycache__', '.stitch'];
  var MAX_FILES = 80;
  var MAX_BYTES = 1.0 * 1024 * 1024;

  function normalizedPath(raw) {
    var parts = String(raw || '').replace(/\\/g, '/').split('/').filter(function (part) {
      return part && part !== '.';
    });
    if (!parts.length || parts.some(function (part) { return part === '..'; })) return '';
    if (parts.some(function (part) { return SKIP_PARTS.indexOf(part) >= 0; })) return '';
    return parts.join('/');
  }

  function extension(path) {
    var match = /\.([a-z0-9]+)$/i.exec(path);
    return match ? '.' + match[1].toLowerCase() : '';
  }

  async function readFolder(input, limits) {
    var options = limits || {};
    var maxFiles = Number(options.maxFiles) || MAX_FILES;
    var maxBytes = Number(options.maxBytes) || MAX_BYTES;
    var entries = Array.from((input && input.files) || []).map(function (file) {
      return { file: file, path: normalizedPath(file.webkitRelativePath || file.name) };
    }).filter(function (entry) { return entry.path; });

    var accepted = [];
    var skipped = [];
    var seen = {};
    entries.forEach(function (entry) {
      var path = entry.path;
      var ext = extension(path);
      if (ALLOWED.indexOf(ext) < 0) { skipped.push(path + ' (unsupported type)'); return; }
      if (seen[path]) { skipped.push(path + ' (duplicate)'); return; }
      if (entry.file.size > 400000) { skipped.push(path + ' (larger than 400 KB)'); return; }
      seen[path] = true;
      accepted.push(entry);
    });
    if (accepted.length > maxFiles) {
      throw new Error('Select at most ' + maxFiles + ' text files.');
    }
    if (!accepted.length) {
      throw new Error('No supported text files were found in that folder.');
    }

    // Strip the selected folder's own name when it is a common first segment.
    var roots = accepted.map(function (entry) { return entry.path.split('/')[0]; });
    var stripRoot = accepted.every(function (entry) { return entry.path.indexOf('/') > 0; }) &&
      roots.every(function (root) { return root === roots[0]; });
    accepted.forEach(function (entry) {
      if (stripRoot) entry.path = entry.path.split('/').slice(1).join('/');
    });

    var files = [];
    var total = 0;
    for (var index = 0; index < accepted.length; index += 1) {
      var entry = accepted[index];
      var text;
      try { text = await entry.file.text(); }
      catch (error) { skipped.push(entry.path + ' (could not read)'); continue; }
      var bytes = new Blob([text]).size;
      if (total + bytes > maxBytes) {
        throw new Error('The selected folder is larger than ' + Math.round(maxBytes / 1024) + ' KB of text.');
      }
      total += bytes;
      files.push({ path: entry.path, content: text });
    }
    if (!files.some(function (file) { return file.path === 'index.html'; })) {
      throw new Error('The folder must contain an index.html at its root.');
    }
    return { files: files, skipped: skipped, bytes: total, root: stripRoot ? roots[0] : '' };
  }

  window.StitchcraftImport = { readFolder: readFolder, allowed: ALLOWED.slice(), maxFiles: MAX_FILES, maxBytes: MAX_BYTES };
})();
