//using System;
//using System.Collections.Generic;
//using System.IO;
//using System.Linq;

//using WriterWorker.Models;
//using WriterWorker.Parser.BacklogParser;
//using WriterWorker.Parser.PipelineParser.Contents;
//using WriterWorker.Parser.PublishedParser;
//using WriterWorker.Parser.PublishedParser.Contents;

//namespace WriterWorker.Controller
//{
//    /// <summary>
//    /// Entry point the application uses to turn a folder into a <see cref="Book"/>: it picks the
//    /// parser for the folder and hands back the model, so no page, list or window ever opens a
//    /// workspace file. Parsers are tried in the order published, backlog, pipeline, because a
//    /// published version folder can also look like a plain folder of files.
//    /// </summary>
//    public static class BookParsers
//    {
//        /// <summary>Every parser the application knows, in the order they are tried.</summary>
//        public static IReadOnlyList<IBookParser> All { get; } =
//        [
//            PublishedBookParser.Instance,
//            BacklogBookParser.Instance,
//            ConfigToModel.Instance,
//        ];

//        /// <summary>The parser that understands the folder, or null when none does.</summary>
//        public static IBookParser? For(string? folder) => All.FirstOrDefault(parser => parser.CanParse(folder));

//        /// <summary>Reads the book in the folder. Throws when the folder holds no readable book.</summary>
//        public static Book Parse(string? folder)
//        {
//            var parser = For(folder) ?? throw new InvalidOperationException(Describe(folder));
//            var resolved = parser.Resolve(folder!) ?? throw new InvalidOperationException(Describe(folder));

//            return parser.Parse(resolved);
//        }

//        /// <summary>Reads the book in the folder, returning null and the reason when it cannot be read.</summary>
//        public static Book? TryParse(string? folder, out string? error)
//        {
//            var parser = For(folder);
//            if (parser is null)
//            {
//                error = Describe(folder);
//                return null;
//            }

//            return parser.TryParse(folder, out error);
//        }

//        /// <summary>
//        /// Explains why no parser accepted the folder: it is missing, it holds several books, or it
//        /// is not a book folder at all. Used for the status bar when "Bind Book" cannot open it.
//        /// </summary>
//        public static string Describe(string? folder)
//        {
//            if (string.IsNullOrWhiteSpace(folder))
//            {
//                return "Select a book folder.";
//            }

//            if (!Directory.Exists(folder))
//            {
//                return $"Folder not found: {folder}";
//            }

//            var name = Path.GetFileName(folder.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
//            if (string.IsNullOrEmpty(name))
//            {
//                name = folder;
//            }

//            if (PublishedLibrary.ContainsBooks(folder))
//            {
//                var books = PublishedLibrary.Scan(folder).Select(book => book.DisplayName).ToList();
//                return $"{name} holds {books.Count} published book(s); bind one of them: {string.Join(", ", books)}";
//            }

//            if (BookLibrary.ContainsBooks(folder))
//            {
//                var books = BookLibrary.Scan(folder).Select(book => book.DisplayName).ToList();
//                return $"{name} holds {books.Count} book(s); bind one of them: {string.Join(", ", books)}";
//            }

//            if (PublishedVersion.IsVersionFolder(folder))
//            {
//                return $"{name} is a published version folder but it holds no readable edition.";
//            }

//            if (BookLibrary.IsBookFolder(folder))
//            {
//                return $"{name} is a book folder but it is neither inside a pipeline folder nor a backlog folder.";
//            }

//            return $"{name} is not a book folder: it holds no book.json, no chapters folder and no published version.";
//        }
//    }
//}
