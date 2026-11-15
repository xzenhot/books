using System;
using System.IO;

using WriterWorker.Controller;
using WriterWorker.Models;
using WriterWorker.Parser.PipelineParser.Contents;

namespace WriterWorker.Parser.BacklogParser
{
    /// <summary>
    /// Reads a book that only exists as a plan, for example
    /// <c>writer\.framework\templates\backlog\v1</c>: a folder below a <c>backlog</c> folder that
    /// holds <c>book.json</c> and a progress report but no chapter text. The plan is projected onto
    /// the same <see cref="Book"/> the pipeline produces, so the pages and the PDF export render a
    /// backlog book without knowing where it came from.
    /// </summary>
    internal sealed class BacklogBookParser : IBookParser
    {
        /// <summary>Parser for backlog books; it holds no state, so one instance is shared.</summary>
        public static BacklogBookParser Instance { get; } = new();

        private BacklogBookParser()
        {
        }

        public BookSource Source => BookSource.Backlog;

        /// <summary>A book folder whose parent chain contains a <c>backlog</c> folder.</summary>
        public bool CanParse(string? folder) =>
            folder is { Length: > 0 } && BookLibrary.IsBookFolder(folder) && IsBelowBacklog(folder);

        public string? Resolve(string folder) => BookLibrary.IsBookFolder(folder) ? folder : null;

        public Book Parse(string folder) =>
            ConfigToModel.FromConfigurationParser(BookContent.Load(folder), BookSource.Backlog);

        private static bool IsBelowBacklog(string folder)
        {
            string full;
            try
            {
                full = Path.GetFullPath(folder);
            }
            catch (Exception exception) when (exception is ArgumentException or NotSupportedException)
            {
                return false;
            }

            for (var parent = Directory.GetParent(full); parent is not null; parent = parent.Parent)
            {
                if (string.Equals(parent.Name, "backlog", StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            return false;
        }
    }
}
