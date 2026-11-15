using System;
using System.Windows;

namespace WriterWorker.Views
{
    /// <summary>
    /// Describes a book page the browser wants the host to show, normally as a tab.
    /// </summary>
    public sealed class BookPageRequest
    {
        /// <summary>Title shown on the tab.</summary>
        public required string Title { get; init; }

        /// <summary>Segoe MDL2 Assets glyph shown in front of the title.</summary>
        public string Glyph { get; init; } = BookGlyphs.Book;

        /// <summary>
        /// Identity of the page. When the host already shows a page with the same key it
        /// activates that page instead of adding a duplicate.
        /// </summary>
        public string? Key { get; init; }

        /// <summary>The page itself.</summary>
        public required FrameworkElement Content { get; init; }
    }

    /// <summary>
    /// Implemented by the application shell (the main window) so the book pages can be shown as
    /// tabs instead of modal dialogs.
    /// </summary>
    public interface IBookPageHost
    {
        /// <summary>Shows a page, or activates it when a page with the same key is already open.</summary>
        void ShowPage(BookPageRequest request);

        /// <summary>Closes the tab that hosts <paramref name="page"/>.</summary>
        void ClosePage(FrameworkElement page);

        /// <summary>Renames the tab that hosts <paramref name="page"/>.</summary>
        void UpdatePageTitle(FrameworkElement page, string title);
    }

    /// <summary>Glyphs of the book browser pages, from Segoe MDL2 Assets.</summary>
    public static class BookGlyphs
    {
        public const string BookList = "\uE8F1";
        public const string Book = "\uE82D";
        public const string Chapter = "\uE8A5";
        public const string Segment = "\uE7C3";
    }

    /// <summary>
    /// Implemented by the pages so the host can read the tab title a page wants to be shown
    /// with, even when the page was just created.
    /// </summary>
    public interface IBookPage
    {
        string Title { get; }
    }
}
