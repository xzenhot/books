using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

using WriterWorker.Parser.PipelineParser.Models;

namespace WriterWorker.Parser.PipelineParser.Contents
{
    /// <summary>
    /// Finds the book folders of a pipeline root (for example
    /// <c>...\writer\workspaces\pipeline</c>) and reads their <c>book.json</c> plans.
    /// </summary>
    public static class BookLibrary
    {
        /// <summary>Folders checked below a selected folder to locate the pipeline root.</summary>
        private static readonly string[] RootCandidates =
        [
            "pipeline",
            Path.Combine("workspaces", "pipeline"),
            Path.Combine("writer", "workspaces", "pipeline"),
        ];

        private static readonly JsonSerializerOptions JsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            ReadCommentHandling = JsonCommentHandling.Skip,
            AllowTrailingCommas = true,
        };

        /// <summary>
        /// Turns any selected folder into the folder that holds books: the folder itself, its
        /// parent when a book folder was selected, or a known pipeline folder below it.
        /// </summary>
        public static string? ResolveRoot(string? folder)
        {
            var full = ToExistingDirectory(folder);
            if (full is null)
            {
                return null;
            }

            // A single book was selected: list its siblings.
            if (IsBookFolder(full))
            {
                return Path.GetDirectoryName(full) ?? full;
            }

            if (ContainsBooks(full))
            {
                return full;
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

        /// <summary>Locates the pipeline folder without user input, walking up from the app and working directory.</summary>
        public static string? FindDefaultRoot()
        {
            var fromEnvironment = ResolveRoot(Environment.GetEnvironmentVariable("BOOKBINDER_PIPELINE"));
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

        /// <summary>A book folder holds a plan, a chapters folder, or both.</summary>
        public static bool IsBookFolder(string folder) =>
            File.Exists(Path.Combine(folder, "book.json")) || Directory.Exists(Path.Combine(folder, "chapters"));

        /// <summary>
        /// A book of a pipeline: a book folder whose parent chain contains a folder named
        /// <c>pipeline</c> (for example <c>...\writer\workspaces\pipeline\nouka</c>).
        /// </summary>
        public static bool IsPipelineBook(string? folder)
        {
            var full = ToExistingDirectory(folder);
            if (full is null || !IsBookFolder(full))
            {
                return false;
            }

            for (var parent = Directory.GetParent(full); parent is not null; parent = parent.Parent)
            {
                if (string.Equals(parent.Name, "pipeline", StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            return false;
        }

        public static bool ContainsBooks(string folder) =>
            Directory.Exists(folder) && EnumerateBookFolders(folder).Any();

        /// <summary>Reads every book of the root folder; unreadable plans keep the folder in the list with an error.</summary>
        public static IReadOnlyList<BookEntry> Scan(string? rootFolder)
        {
            var root = ToExistingDirectory(rootFolder);
            if (root is null)
            {
                return [];
            }

            var books = new List<BookEntry>();
            foreach (var directory in EnumerateBookFolders(root))
            {
                var book = new BookEntry(directory);
                book.Plan = ReadPlan(directory, out var error);
                book.Error = error;

                var chapters = Path.Combine(directory, "chapters");
                if (Directory.Exists(chapters))
                {
                    var chapterFolders = Directory.GetDirectories(chapters);
                    book.ChapterFolderCount = chapterFolders.Length;
                    book.SegmentFolderCount = chapterFolders.Sum(CountSegments);
                }

                books.Add(book);
            }

            return books;
        }

        /// <summary>Reads <c>book.json</c>; a malformed plan returns null and reports the reason.</summary>
        public static BookModel? ReadPlan(string folder, out string? error)
        {
            error = null;
            var path = Path.Combine(folder, "book.json");
            if (!File.Exists(path))
            {
                error = "book.json not found";
                return null;
            }

            try
            {
                var text = File.ReadAllText(path);
                return string.IsNullOrWhiteSpace(text)
                    ? null
                    : JsonSerializer.Deserialize<BookModel>(text, JsonOptions);
            }
            catch (JsonException exception)
            {
                error = exception.Message;
                return null;
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                error = exception.Message;
                return null;
            }
        }

        /// <summary>Reads the full workspace content of a book (plan, progress, chapters, segments, documents).</summary>
        public static BookContent Open(BookEntry book)
        {
            ArgumentNullException.ThrowIfNull(book);
            return BookContent.Load(book.FolderPath);
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
                .Where(IsBookFolder)
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

        private static int CountSegments(string chapterFolder)
        {
            var segments = Path.Combine(chapterFolder, "segments");
            return Directory.Exists(segments) ? Directory.GetDirectories(segments).Length : 0;
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
