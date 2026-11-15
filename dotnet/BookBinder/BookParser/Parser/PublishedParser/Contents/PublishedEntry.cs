using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace WriterWorker.Parser.PublishedParser.Contents
{
    /// <summary>
    /// One published book folder (for example <c>...\writer\workspaces\published\nouka</c>) with the
    /// version folders the publish step has cut into it.
    /// </summary>
    public sealed class PublishedEntry
    {
        public PublishedEntry(string folderPath)
        {
            FolderPath = Path.GetFullPath(folderPath);
            FolderName = Path.GetFileName(
                FolderPath.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
            if (string.IsNullOrEmpty(FolderName))
            {
                FolderName = FolderPath;
            }
        }

        public string FolderPath { get; }

        public string FolderName { get; }

        /// <summary>Book title read from the <c>book.md</c> heading of the newest version.</summary>
        public string? Title { get; set; }

        /// <summary>Why the book folder could not be read, or null when it was.</summary>
        public string? Error { get; set; }

        /// <summary>Versions found on disk, oldest first.</summary>
        public List<PublishedVersion> Versions { get; } = [];

        public PublishedVersion? Latest => Versions.Count == 0 ? null : Versions[^1];

        public int VersionCount => Versions.Count;

        public string? PublishedAt => Latest?.PublishedAt;

        public string DisplayName =>
            new[] { Title, FolderName }.FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ?? FolderName;

        public override string ToString() => DisplayName;
    }
}
