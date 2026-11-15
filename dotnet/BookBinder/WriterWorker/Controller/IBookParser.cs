using System;
using System.IO;
using System.Text.Json;
using WriterWorker.Models;

namespace WriterWorker.Controller
{
    /// <summary>
    /// Reads one kind of book folder into the model the pages and the PDF export render
    /// (<see cref="Book"/>), so the UI never opens a workspace file itself. Every tree the
    /// application understands - the pipeline, the backlog templates and the published editions -
    /// has its own implementation, and <see cref="BookParsers"/> picks the right one.
    /// </summary>
    public interface IBookParser
    {
        /// <summary>Tree this parser reads; also set on the books it returns.</summary>
        BookSource Source { get; }

        /// <summary>
        /// True when <paramref name="folder"/> is a folder this parser understands: a book folder,
        /// or one of the folders inside it (a version folder, for example).
        /// </summary>
        bool CanParse(string? folder);

        /// <summary>
        /// Folder <see cref="Parse"/> should be handed for a folder <see cref="CanParse"/> accepted,
        /// for example the newest version of a published book. Null when the folder holds nothing
        /// to read.
        /// </summary>
        string? Resolve(string folder);

        /// <summary>Reads the folder and returns the book. Throws when the folder cannot be read.</summary>
        Book Parse(string folder);

        /// <summary>
        /// Reads the folder, returning null and the reason when it cannot be read. Unreadable
        /// folders and broken files are reported, not thrown, because the UI asks for books the
        /// user picked from a tree.
        /// </summary>
        Book? TryParse(string? folder, out string? error)
        {
            error = null;

            if (!CanParse(folder))
            {
                return null;
            }

            var resolved = Resolve(folder!);
            if (string.IsNullOrWhiteSpace(resolved))
            {
                error = $"{Source} folder holds nothing to read: {folder}";
                return null;
            }

            try
            {
                return Parse(resolved);
            }
            catch (Exception exception) when (exception is IOException
                or UnauthorizedAccessException
                or InvalidDataException
                or InvalidOperationException
                or NotSupportedException
                or ArgumentException
                or JsonException)
            {
                error = exception.Message;
                return null;
            }
        }
    }
}

