using System;
using System.Collections.Generic;
using System.Linq;

namespace WriterWorker.Models
{
    /// <summary>
    /// Pipeline folder the book pages read segment text from. The choice is cached in a static
    /// property so every page opened during the session, and the PDF export, sees the same source.
    /// </summary>
    public static class ContentSource
    {
        public const string Latest = "Latest";
        public const string Editor = "Editor";
        public const string Translated = "Translated";
        public const string Writer = "Writer";

        /// <summary>Choices offered in the content-source dropdown.</summary>
        public static IReadOnlyList<string> Options { get; } = [Latest, Editor, Translated, Writer];

        private static string _selected = Latest;

        /// <summary>Selected choice; unknown values fall back to <see cref="Latest"/>.</summary>
        public static string Selected
        {
            get => _selected;
            set => _selected = Options.FirstOrDefault(option =>
                string.Equals(option, value, StringComparison.OrdinalIgnoreCase)) ?? Latest;
        }

        /// <summary>Segment sub-folder that holds the text for a choice, e.g. translator.</summary>
        public static string FolderName(string? source) => source switch
        {
            Editor => "editor",
            Translated => "translator",
            Writer => "writer",
            _ => "latest",
        };
    }
}
