using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

using WriterWorker.Models;
using WriterWorker.Parser.PipelineParser.Contents;
using WriterWorker.Parser.PipelineParser.Models;
using WriterWorker.Parser.PublishedParser.Models;

namespace WriterWorker.Parser.PublishedParser.Contents
{
    /// <summary>
    /// Finds the published book folders below a published root (for example
    /// <c>...\writer\workspaces\published</c>) and the version folders each of them holds.
    /// <para>
    /// The published tree is the read-only side of the writer pipeline: the publish step copies the
    /// chosen segments into <c>published/{book}/version{n}</c> and never edits a version again, so
    /// everything read here is a finished edition of the book.
    /// </para>
    /// </summary>
    public static class PublishedLibrary
    {
        /// <summary>Folders checked below a selected folder to locate the published root.</summary>
        private static readonly string[] RootCandidates =
        [
            "published",
            Path.Combine("workspaces", "published"),
            Path.Combine("writer", "workspaces", "published"),
        ];

        private static readonly JsonSerializerOptions JsonOptions = new()
        {
            PropertyNameCaseInsensitive = true,
            ReadCommentHandling = JsonCommentHandling.Skip,
            AllowTrailingCommas = true,
        };

        /// <summary>
        /// Turns any selected folder into the folder that holds published books: the folder itself,
        /// the parent of a selected book or version folder, or a known published folder below it.
        /// </summary>
        public static string? ResolveRoot(string? folder)
        {
            var full = ToExistingDirectory(folder);
            if (full is null)
            {
                return null;
            }

            // A version folder was selected: its book folder holds the other versions.
            if (PublishedVersion.IsVersionFolder(full))
            {
                full = Directory.GetParent(full)?.FullName ?? full;
            }

            // A single book was selected: list its siblings.
            if (IsPublishedBook(full))
            {
                return Directory.GetParent(full)?.FullName ?? full;
            }

            if (ContainsBooks(full))
            {
                return full;
            }

            // A pipeline folder keeps its published editions in a sibling folder, so selecting
            // ...\workspaces\pipeline (or one of its books) still finds ...\workspaces\published.
            var parent = Directory.GetParent(full)?.FullName;
            if (parent is not null)
            {
                var sibling = Path.Combine(parent, "published");
                if (Directory.Exists(sibling) && ContainsBooks(sibling))
                {
                    return sibling;
                }
            }

            foreach (var candidate in RootCandidates)
            {
                var path = Path.Combine(full, candidate);
                if (Directory.Exists(path) && ContainsBooks(path))
                {
                    return path;
                }
            }

            return full;
        }

        /// <summary>Locates the published folder without user input, walking up from the app and working directory.</summary>
        public static string? FindDefaultRoot()
        {
            var fromEnvironment = ResolveRoot(Environment.GetEnvironmentVariable("BOOKBINDER_PUBLISHED"));
            if (fromEnvironment is not null && ContainsBooks(fromEnvironment))
            {
                return fromEnvironment;
            }

            foreach (var start in new[] { Environment.CurrentDirectory, AppContext.BaseDirectory })
            {
                for (var directory = new DirectoryInfo(start); directory is not null; directory = directory.Parent)
                {
                    foreach (var candidate in RootCandidates)
                    {
                        var path = Path.Combine(directory.FullName, candidate);
                        if (Directory.Exists(path) && ContainsBooks(path))
                        {
                            return path;
                        }
                    }
                }
            }

            return null;
        }

        /// <summary>A published book folder holds at least one readable version folder.</summary>
        public static bool IsPublishedBook(string folder) =>
            Directory.Exists(folder) && EnumerateVersions(folder).Any();

        /// <summary>
        /// A book of the published tree: a book folder whose parent chain contains a folder named
        /// <c>published</c> (for example <c>...\writer\workspaces\published\nouka</c>).
        /// </summary>
        public static bool IsPublishedTree(string? folder)
        {
            var full = ToExistingDirectory(folder);
            if (full is null || !IsPublishedBook(full))
            {
                return false;
            }

            for (var parent = Directory.GetParent(full); parent is not null; parent = parent.Parent)
            {
                if (string.Equals(parent.Name, "published", StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            return false;
        }

        public static bool ContainsBooks(string folder) =>
            Directory.Exists(folder) && EnumerateBookFolders(folder).Any();

        /// <summary>Reads every published book of the root folder; unreadable books keep their error.</summary>
        public static IReadOnlyList<PublishedEntry> Scan(string? rootFolder)
        {
            var root = ToExistingDirectory(rootFolder);
            if (root is null)
            {
                return [];
            }

            var books = new List<PublishedEntry>();
            foreach (var directory in EnumerateBookFolders(root))
            {
                books.Add(Read(directory));
            }

            return books;
        }

        /// <summary>Reads one published book folder: its versions, their manifests and the newest title.</summary>
        public static PublishedEntry Read(string bookFolder)
        {
            var entry = new PublishedEntry(bookFolder);
            try
            {
                foreach (var versionFolder in EnumerateVersions(entry.FolderPath))
                {
                    var version = new PublishedVersion(versionFolder);
                    var manifest = ReadManifest(versionFolder);
                    version.PublishedAt = manifest?.PublishedAt ?? manifest?.UpdatedDate;
                    version.ChapterCount = manifest is { Chapters.Count: > 0 } read
                        ? read.Chapters.Count
                        : CountChapterFolders(versionFolder);
                    entry.Versions.Add(version);
                }

                entry.Versions.Sort((left, right) => left.Number.CompareTo(right.Number));
                entry.Title = ReadBookTitle(entry.Latest);
                if (entry.Versions.Count == 0)
                {
                    entry.Error = "no version folders found";
                }
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                entry.Error = exception.Message;
            }

            return entry;
        }

        /// <summary>
        /// Finds the published book a folder belongs to, so a book folder, one of its version
        /// folders, or a folder that holds exactly one book can all be bound in one step.
        /// The newest version of that book is always the one that gets read.
        /// </summary>
        public static PublishedEntry? FindBook(string? folder)
        {
            var full = ToExistingDirectory(folder);
            if (full is null)
            {
                return null;
            }

            // A version folder stands for the book that holds it.
            if (PublishedVersion.IsVersionFolder(full))
            {
                var parent = Directory.GetParent(full)?.FullName;
                return parent is not null && IsPublishedBook(parent) ? Read(parent) : null;
            }

            if (IsPublishedBook(full))
            {
                return Read(full);
            }

            // A published root or a folder of books stands for its only book.
            if (ContainsBooks(full))
            {
                var books = EnumerateBookFolders(full).ToList();
                if (books.Count == 1)
                {
                    return Read(books[0]);
                }
            }

            return null;
        }

        /// <summary>Reads the full content of a published version as the parser's book content.</summary>
        public static BookContent Open(PublishedVersion version, BookModel? plan = null)
        {
            ArgumentNullException.ThrowIfNull(version);
            return PublishedContentLoader.Load(version.FolderPath, plan);
        }

        /// <summary>
        /// Reads a published version as the book the pages and the PDF export render. This is the entry
        /// point for the UI: everything above it stays inside the parser.
        /// </summary>
        public static Book OpenBook(PublishedVersion version, BookModel? plan = null)
        {
            ArgumentNullException.ThrowIfNull(version);
            return ConfigToModel.FromConfigurationParser(Open(version, plan), BookSource.Published);
        }

        /// <summary>Reads <c>manifest.json</c>; a malformed manifest returns null.</summary>
        public static PublishedManifestModel? ReadManifest(string versionFolder)
        {
            var path = Path.Combine(versionFolder, "manifest.json");
            if (!File.Exists(path))
            {
                return null;
            }

            try
            {
                var text = File.ReadAllText(path);
                return string.IsNullOrWhiteSpace(text)
                    ? null
                    : JsonSerializer.Deserialize<PublishedManifestModel>(text, JsonOptions);
            }
            catch (Exception exception) when (exception is JsonException or IOException or UnauthorizedAccessException)
            {
                return null;
            }
        }

        /// <summary>Book title from the <c>book.md</c> heading of a version.</summary>
        private static string? ReadBookTitle(PublishedVersion? version)
        {
            if (version is null)
            {
                return null;
            }

            var path = Path.Combine(version.FolderPath, "book.md");
            if (!File.Exists(path))
            {
                return null;
            }

            try
            {
                PublishedMarkdown.Read(File.ReadAllText(path), out var heading);
                return heading;
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                return null;
            }
        }

        private static int CountChapterFolders(string versionFolder)
        {
            var chapters = Path.Combine(versionFolder, "chapters");
            return Directory.Exists(chapters) ? Directory.GetDirectories(chapters).Length : 0;
        }

        private static IEnumerable<string> EnumerateVersions(string bookFolder)
        {
            IEnumerable<string> directories;
            try
            {
                directories = Directory.GetDirectories(bookFolder);
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                return [];
            }

            return directories
                .Where(IsVisibleDirectory)
                .Where(PublishedVersion.IsVersionFolder)
                .OrderBy(PublishedVersion.ParseNumber)
                .ThenBy(Path.GetFileName, StringComparer.OrdinalIgnoreCase);
        }

        private static IEnumerable<string> EnumerateBookFolders(string folder)
        {
            IEnumerable<string> directories;
            try
            {
                directories = Directory.GetDirectories(folder);
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                return [];
            }

            return directories
                .Where(IsVisibleDirectory)
                .Where(IsPublishedBook)
                .OrderBy(Path.GetFileName, StringComparer.OrdinalIgnoreCase);
        }

        private static bool IsVisibleDirectory(string directory)
        {
            try
            {
                return (File.GetAttributes(directory) & FileAttributes.Hidden) == 0;
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                return false;
            }
        }

        private static string? ToExistingDirectory(string? folder)
        {
            if (string.IsNullOrWhiteSpace(folder))
            {
                return null;
            }

            try
            {
                var full = Path.GetFullPath(folder);
                if (File.Exists(full))
                {
                    full = Path.GetDirectoryName(full) ?? full;
                }

                return Directory.Exists(full) ? full : null;
            }
            catch (Exception exception) when (exception is ArgumentException or IOException or NotSupportedException)
            {
                return null;
            }
        }
    }
}
