using System;
using System.Globalization;
using System.IO;
using System.Text.RegularExpressions;

namespace WriterWorker.Parser.PublishedParser.Contents
{
    /// <summary>
    /// One immutable publication folder, for example
    /// <c>...\writer\workspaces\published\nouka\version6</c>. The publish step builds the folder
    /// privately and renames it into place, so a version never changes once it appears.
    /// </summary>
    internal sealed class PublishedVersion
    {
        private static readonly Regex NumberPattern = new(@"^(?:version)?(\d+)$", RegexOptions.IgnoreCase);

        public PublishedVersion(string folderPath)
        {
            FolderPath = Path.GetFullPath(folderPath);
            FolderName = Path.GetFileName(
                FolderPath.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
            if (string.IsNullOrEmpty(FolderName))
            {
                FolderName = FolderPath;
            }

            Number = ParseNumber(FolderName);
        }

        public string FolderPath { get; }

        /// <summary>Folder name, for example <c>version6</c>.</summary>
        public string FolderName { get; }

        /// <summary>Version number taken from the folder name; 0 when the folder is not numbered.</summary>
        public int Number { get; }

        /// <summary>Publication timestamp from <c>manifest.json</c>.</summary>
        public string? PublishedAt { get; set; }

        /// <summary>Chapter folders found in the version, used when the manifest does not list them.</summary>
        public int ChapterCount { get; set; }

        public bool HasManifest => File.Exists(Path.Combine(FolderPath, "manifest.json"));

        /// <summary>The whole book assembled by the publish step (<c>book.md</c>).</summary>
        public bool HasBook => File.Exists(Path.Combine(FolderPath, "book.md"));

        /// <summary>A folder that holds a manifest, the whole-book markdown or chapter folders.</summary>
        public bool IsReadable =>
            HasManifest || HasBook || Directory.Exists(Path.Combine(FolderPath, "chapters"));

        public string DisplayName =>
            Number > 0 ? "version" + Number.ToString(CultureInfo.InvariantCulture) : FolderName;

        /// <summary>True when the folder name is a version number and the folder holds published files.</summary>
        public static bool IsVersionFolder(string? folder)
        {
            if (string.IsNullOrWhiteSpace(folder) || !Directory.Exists(folder))
            {
                return false;
            }

            var name = Path.GetFileName(Path.GetFullPath(folder).TrimEnd(
                Path.DirectorySeparatorChar,
                Path.AltDirectorySeparatorChar));

            return ParseNumber(name) > 0
                && (File.Exists(Path.Combine(folder, "manifest.json"))
                    || File.Exists(Path.Combine(folder, "book.md"))
                    || Directory.Exists(Path.Combine(folder, "chapters")));
        }

        /// <summary>Reads <c>version6</c> as 6 and keeps the legacy bare <c>6</c> folder names working.</summary>
        public static int ParseNumber(string? name)
        {
            if (string.IsNullOrWhiteSpace(name))
            {
                return 0;
            }

            var match = NumberPattern.Match(name.Trim());
            return match.Success
                   && int.TryParse(match.Groups[1].Value, NumberStyles.Integer, CultureInfo.InvariantCulture, out var number)
                ? number
                : 0;
        }

        public override string ToString() => DisplayName;
    }
}
