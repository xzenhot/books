using WriterWorker.Controller;
using WriterWorker.Models;

namespace WriterWorker.Parser.PublishedParser
{
    /// <summary>
    /// Reads a finished edition: a published book folder
    /// (<c>...\workspaces\published\nouka</c>) or one of its version folders
    /// (<c>...\published\nouka\version6</c>). A book folder always resolves to its newest version,
    /// because a version never changes once the publish step has renamed it into place.
    /// </summary>
    internal sealed class PublishedBookParser : IBookParser
    {
        /// <summary>Parser for published editions; it holds no state, so one instance is shared.</summary>
        public static PublishedBookParser Instance { get; } = new();

        private PublishedBookParser()
        {
        }

        public BookSource Source => BookSource.Published;

        public bool CanParse(string? folder) => Contents.PublishedLibrary.FindBook(folder) is not null;

        /// <summary>The version folder itself, or the newest version of the book folder that holds it.</summary>
        public string? Resolve(string folder) =>
            Contents.PublishedVersion.IsVersionFolder(folder)
                ? folder
                : Contents.PublishedLibrary.FindBook(folder)?.Latest?.FolderPath;

        public Book Parse(string folder) =>
            Contents.PublishedLibrary.OpenBook(new Contents.PublishedVersion(folder));
    }
}
