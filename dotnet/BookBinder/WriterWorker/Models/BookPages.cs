using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace WriterWorker.Models;

/// <summary>What a page folder holds, as the <c>format</c> of the folder records it.</summary>
public enum PageFormat
{
    /// <summary>Images printed edge to edge, one page each - the covers.</summary>
    Image,

    /// <summary>Rich text designs, one page each - the blurb, the publisher pages and the appendix.</summary>
    Rtf,

    /// <summary>Pages the export generates from the book itself - the index and the chapters.</summary>
    Markdown
}

/// <summary>
/// The part of the book a page folder belongs to. It decides how the folder prints - the cover as
/// images, the publisher pages as designs, the content from the chapters - and where a page of that
/// part is listed in the setup window.
/// </summary>
public enum PageGroupRole
{
    Cover,
    Blurb,
    Publisher,
    Index,
    Content,
    Appendix,

    /// <summary>Images printed after every other page, closing the book - the back cover.</summary>
    BackCover,

    /// <summary>A folder of the workspace this app has no rule for; printed after the parts it knows.</summary>
    Other
}

/// <summary>
/// One page of the book: a file of a page folder, the position it prints in and the kind of file it
/// is, as the <c>paths</c> of the folder record it -
/// <c>{"order": 1, "file_path": "pages/publisher/title.rtf", "content_type": "application/rtf"}</c>.
/// </summary>
public sealed class BookPageFile
{
    /// <summary>Position of the page in its folder, from one.</summary>
    public int Order { get; set; }

    /// <summary>File of the page, relative to the book folder.</summary>
    public string FilePath { get; set; } = string.Empty;

    /// <summary>
    /// Kind of the file as its MIME type - <c>application/rtf</c>, <c>text/markdown</c>,
    /// <c>image/jpeg</c>. It is what the page is printed as; the <c>format</c> of the folder is only
    /// the preference a page falls back on when it records none of its own.
    /// </summary>
    public string ContentType { get; set; } = string.Empty;

    /// <summary>Name of the page without its folder or extension, for example <c>title</c>.</summary>
    public string Name => BookPages.NameOfFile(FilePath);

    /// <summary>Extension of the file in lower case, without the dot.</summary>
    public string Extension => Path.GetExtension(FilePath).TrimStart('.').ToLowerInvariant();

    /// <summary>What the page is printed as: its own content type, or the preference of its folder.</summary>
    public PageFormat Format => BookPages.FormatOf(this, PageFormat.Rtf);

    public BookPageFile Clone() => new() { Order = Order, FilePath = FilePath, ContentType = ContentType };

    public override string ToString() => $"{Order}:{FilePath} ({ContentType})";
}

/// <summary>
/// One page folder of the book in print order: the folder, the format of the pages it holds and the
/// pages themselves. The folder of a book is <c>pages/cover</c>, <c>pages/blurb</c>,
/// <c>pages/publisher</c>, <c>pages/index</c>, <c>pages/content</c>, <c>pages/appendix</c> or
/// <c>pages/backcover</c>; the order of the folders and the order of the pages inside them are
/// recorded in the <c>config.json</c> of the book, so neither a folder nor a file carries a number.
/// </summary>
public sealed class BookPageGroup
{
    /// <summary>Position of the folder in the book, from one.</summary>
    public int Order { get; set; }

    /// <summary>Folder of the pages, relative to the book folder, ending in a slash - <c>pages/publisher/</c>.</summary>
    public string FilePath { get; set; } = string.Empty;

    /// <summary>What the folder holds.</summary>
    public PageFormat Format { get; set; } = PageFormat.Rtf;

    /// <summary>The pages of the folder.</summary>
    public List<BookPageFile> Files { get; set; } = [];

    /// <summary>Name of the folder without its order prefix, for example <c>publisher</c>.</summary>
    public string Name => BookPages.NameOfFolder(FilePath);

    /// <summary>The part of the book the folder belongs to.</summary>
    public PageGroupRole Role => BookPages.RoleOf(Name);

    /// <summary>Name of the part as the author sees it, for example <c>Publisher</c>.</summary>
    public string DisplayName => BookPages.DisplayNameOf(Role);

    /// <summary>The pages in the order they print.</summary>
    public IEnumerable<BookPageFile> Printed => BookPages.PrintedFiles(this);

    /// <summary>Adds a page where the design of its part of the book belongs unless it is listed already.</summary>
    public BookPageFile Add(string relativePath)
    {
        var path = BookPages.Normalize(relativePath);

        if (Files.FirstOrDefault(file => BookPages.SamePath(file.FilePath, path)) is { } listed)
        {
            return listed;
        }

        var added = new BookPageFile
        {
            Order = BookPages.DefaultOrderOfFile(Role, BookPages.NameOfFile(path)),
            FilePath = path,
            ContentType = BookPages.ContentTypeOf(path, Format)
        };

        Files.Add(added);
        return added;
    }

    /// <summary>Drops a page from the folder, leaving the file on disk.</summary>
    public bool Remove(string relativePath) =>
        Files.RemoveAll(file => BookPages.SamePath(file.FilePath, BookPages.Normalize(relativePath))) > 0;

    /// <summary>Ranks the pages from one in the order they print.</summary>
    public BookPageGroup Rank()
    {
        var position = 0;

        foreach (var file in Printed.ToList())
        {
            file.Order = ++position;
        }

        return this;
    }

    public BookPageGroup Clone() => new()
    {
        Order = Order,
        FilePath = FilePath,
        Format = Format,
        Files = Files.Select(file => file.Clone()).ToList()
    };

    public override string ToString() => $"{Order}:{FilePath} ({Format}, {Files.Count} pages)";
}

/// <summary>
/// The pages of a book, read from the <c>pages</c> section of its <c>config.json</c>: the page
/// folders in print order, each with the format of the pages it holds and the pages themselves in
/// the order they print. There is no other record of the pages - every page of the book, the covers
/// and the chapters included, is a file of one of these folders - so the export, the setup window
/// and the designer all read and write this one structure.
/// </summary>
public static class BookPages
{
    /// <summary>Folder of the book the page folders are kept in.</summary>
    public const string FolderName = "pages";

    /// <summary>Folder older designs were kept in; read and moved, never written.</summary>
    public const string LegacyFolderName = "layout";

    /// <summary>Extension of the rich text designs.</summary>
    public const string RtfExtension = ".rtf";

    /// <summary>Content type of a rich text design.</summary>
    public const string RtfContentType = "application/rtf";

    /// <summary>Content type of a page the export writes from the book itself.</summary>
    public const string MarkdownContentType = "text/markdown";

    /// <summary>Content type of the covers and the other pages printed as they are.</summary>
    public const string JpegContentType = "image/jpeg";

    /// <summary>Content type of a file this app does not know the kind of.</summary>
    public const string UnknownContentType = "application/octet-stream";

    /// <summary>Name a page with nothing on it is kept under - <c>blank.rtf</c>, then <c>blank-2.rtf</c>.</summary>
    public const string BlankName = "blank";

    /// <summary>The parts of a book this app knows, in the order a new book prints them.</summary>
    public static readonly IReadOnlyList<PageGroupRole> Roles = new[]
    {
        PageGroupRole.Cover,
        PageGroupRole.Blurb,
        PageGroupRole.Publisher,
        PageGroupRole.Index,
        PageGroupRole.Content,
        PageGroupRole.Appendix,
        PageGroupRole.BackCover
    };

    /// <summary>Folder name of a part of the book, for example <c>publisher</c>.</summary>
    public static string NameOfRole(PageGroupRole role) =>
        role == PageGroupRole.Other ? "pages" : role.ToString().ToLowerInvariant();

    /// <summary>
    /// The part of the book a folder name stands for. The names are the ones the workspace uses -
    /// <c>cover</c>, <c>blurb</c>, <c>publisher</c>, <c>index</c>, <c>content</c>, <c>appendix</c>,
    /// <c>backcover</c> - and an order prefix of an older version is ignored.
    /// </summary>
    public static PageGroupRole RoleOf(string? name) => NameOfFolder(name) switch
    {
        "cover" or "covers" => PageGroupRole.Cover,
        "blurb" or "blurbs" => PageGroupRole.Blurb,
        "publisher" or "publishers" or "imprint" => PageGroupRole.Publisher,
        "index" or "contents" or "toc" => PageGroupRole.Index,
        "content" or "contents" or "chapters" or "body" => PageGroupRole.Content,
        "appendix" or "appendices" or "annex" => PageGroupRole.Appendix,
        "backcover" or "backcovers" or "back-cover" or "back_cover" or "closing" => PageGroupRole.BackCover,
        _ => PageGroupRole.Other
    };

    /// <summary>Format of the pages of a part of the book.</summary>
    public static PageFormat FormatOf(PageGroupRole role) => role switch
    {
        PageGroupRole.Cover or PageGroupRole.BackCover => PageFormat.Image,
        PageGroupRole.Index or PageGroupRole.Content => PageFormat.Markdown,
        _ => PageFormat.Rtf
    };

    /// <summary>The format a <c>format</c> of the configuration stands for; rich text when it says nothing.</summary>
    public static PageFormat ParseFormat(string? format) => format?.Trim().ToLowerInvariant() switch
    {
        "image" or "images" or "img" or "jpg" or "jpeg" or "png" => PageFormat.Image,
        "markdown" or "md" or "markdown-pages" => PageFormat.Markdown,
        _ => PageFormat.Rtf
    };

    /// <summary>The <c>format</c> of the configuration for a format.</summary>
    public static string FormatName(PageFormat format) => format.ToString().ToLowerInvariant();

    /// <summary>The content type a folder of <paramref name="format"/> prefers for its pages.</summary>
    public static string ContentTypeOf(PageFormat format) => format switch
    {
        PageFormat.Image => JpegContentType,
        PageFormat.Markdown => MarkdownContentType,
        _ => RtfContentType
    };

    /// <summary>
    /// The content type a file is printed as, from its extension - <c>front.jpg</c> is
    /// <c>image/jpeg</c>, <c>title.rtf</c> is <c>application/rtf</c> - or the preference of its
    /// folder when the extension says nothing.
    /// </summary>
    public static string ContentTypeOf(string? path, PageFormat preference) =>
        ContentTypeOfExtension(path) ?? ContentTypeOf(preference);

    /// <summary>
    /// The content type a page is printed as: the one it records, then the one its extension gives,
    /// then the preference of its folder. A profile that records no <c>content_type</c> is read the
    /// way it was written before content types existed.
    /// </summary>
    public static string ContentTypeOf(BookPageFile file, PageFormat preference) =>
        (string.IsNullOrWhiteSpace(file.ContentType) ? null : file.ContentType.Trim())
        ?? ContentTypeOf(file.FilePath, preference);

    /// <summary>
    /// The format a content type is printed as - an image, a rich text design or a page the export
    /// writes - or <c>null</c> when the type names neither.
    /// </summary>
    public static PageFormat? ParseContentType(string? contentType)
    {
        var type = (contentType ?? string.Empty).Trim().ToLowerInvariant();

        if (type.Length == 0)
        {
            return null;
        }

        if (type.StartsWith("image/", StringComparison.Ordinal))
        {
            return PageFormat.Image;
        }

        return type switch
        {
            RtfContentType or "text/rtf" or "application/x-rtf" or "text/richtext" => PageFormat.Rtf,
            MarkdownContentType or "text/x-markdown" => PageFormat.Markdown,
            _ => null
        };
    }

    /// <summary>The format a page is printed as, taking its recorded content type before the preference of its folder.</summary>
    public static PageFormat FormatOf(BookPageFile file, PageFormat preference) =>
        ParseContentType(ContentTypeOf(file, preference)) ?? preference;

    /// <summary>The content type an extension gives, or <c>null</c> when this app does not know it.</summary>
    public static string? ContentTypeOfExtension(string? path) =>
        Path.GetExtension(Normalize(path)).ToLowerInvariant() switch
        {
            ".jpg" or ".jpeg" or ".jpe" => "image/jpeg",
            ".png" => "image/png",
            ".gif" => "image/gif",
            ".bmp" => "image/bmp",
            ".tif" or ".tiff" => "image/tiff",
            ".webp" => "image/webp",
            ".svg" => "image/svg+xml",
            ".rtf" => RtfContentType,
            ".md" or ".markdown" => MarkdownContentType,
            ".txt" => "text/plain",
            ".html" or ".htm" => "text/html",
            ".pdf" => "application/pdf",
            _ => null
        };

    /// <summary>Name of a part of the book as the author sees it, for example <c>Publisher</c>.</summary>
    public static string DisplayNameOf(PageGroupRole role) => role switch
    {
        PageGroupRole.Cover => "Cover",
        PageGroupRole.Blurb => "Blurb",
        PageGroupRole.Publisher => "Publisher",
        PageGroupRole.Index => "Index",
        PageGroupRole.Content => "Content",
        PageGroupRole.Appendix => "Appendix",
        PageGroupRole.BackCover => "Back cover",
        _ => "Pages"
    };

    /// <summary>Position of a part in the book when the configuration records none.</summary>
    public static int DefaultOrderOf(PageGroupRole role)
    {
        for (var index = 0; index < Roles.Count; index++)
        {
            if (Roles[index] == role)
            {
                return index + 1;
            }
        }

        return Roles.Count + 1;
    }

    /// <summary>Folder of a part of the book as the configuration writes it, ending in a slash.</summary>
    public static string FolderPathOf(PageGroupRole role) => $"{FolderName}/{NameOfRole(role)}/";

    /// <summary>The seven page folders a new book starts with, in print order.</summary>
    public static IReadOnlyList<BookPageGroup> DefaultGroups() =>
        Roles.Select(role => new BookPageGroup
        {
            Order = DefaultOrderOf(role),
            FilePath = FolderPathOf(role),
            Format = FormatOf(role),
            Files = []
        }).ToList();

    /// <summary>The groups in the order they print.</summary>
    public static IReadOnlyList<BookPageGroup> Ordered(IEnumerable<BookPageGroup> groups) =>
        groups
            .OrderBy(group => group.Order > 0 ? group.Order : DefaultOrderOf(group.Role))
            .ThenBy(group => DefaultOrderOf(group.Role))
            .ThenBy(group => group.FilePath, StringComparer.OrdinalIgnoreCase)
            .ToList();

    /// <summary>
    /// The pages of a group in the order they print: the recorded order, then the position the design
    /// of the page has in its part of the book, then the name.
    /// </summary>
    public static IEnumerable<BookPageFile> PrintedFiles(BookPageGroup group) =>
        group.Files
            .OrderBy(file => file.Order > 0 ? file.Order : DefaultOrderOfFile(group.Role, file.Name))
            .ThenBy(file => file.Name, StringComparer.OrdinalIgnoreCase)
            .ThenBy(file => file.FilePath, StringComparer.OrdinalIgnoreCase);

    /// <summary>
    /// Position a design has in the pages of its part of the book - <c>title</c> comes before
    /// <c>publisher</c>, which comes before the dedication - or the position after the last design
    /// when the part has no rule for the name.
    /// </summary>
    public static int DefaultOrderOfFile(PageGroupRole role, string? name)
    {
        var names = DesignNamesOf(role);

        for (var index = 0; index < names.Count; index++)
        {
            if (string.Equals(names[index], (name ?? string.Empty).Trim(), StringComparison.OrdinalIgnoreCase))
            {
                return index + 1;
            }
        }

        return names.Count + 1;
    }

    /// <summary>Absolute path of a file or folder recorded relative to <paramref name="bookFolder"/>.</summary>
    public static string? Resolve(string? bookFolder, string? relativePath)
    {
        if (string.IsNullOrWhiteSpace(bookFolder) || string.IsNullOrWhiteSpace(relativePath))
        {
            return null;
        }

        var folder = Path.GetFullPath(bookFolder);
        var path = Path.IsPathRooted(relativePath)
            ? relativePath
            : Path.Combine(folder, relativePath.Replace('/', Path.DirectorySeparatorChar));

        return Path.GetFullPath(path);
    }

    /// <summary>Path of <paramref name="path"/> inside the book folder, as the configuration keeps it.</summary>
    public static string Relative(string bookFolder, string path) =>
        Path.GetRelativePath(Path.GetFullPath(bookFolder), Path.GetFullPath(path)).Replace('\\', '/');

    /// <summary>A page path in the form the configuration writes it.</summary>
    public static string Normalize(string? relativePath) =>
        (relativePath ?? string.Empty).Trim().Replace('\\', '/');

    /// <summary>Whether two page paths name the same file.</summary>
    public static bool SamePath(string? left, string? right) =>
        string.Equals(Normalize(left).TrimEnd('/'), Normalize(right).TrimEnd('/'), StringComparison.OrdinalIgnoreCase);

    /// <summary>Name of a page file without its folder or extension, for example <c>title</c>.</summary>
    public static string NameOfFile(string? path) => WithoutOrder(Path.GetFileNameWithoutExtension(Normalize(path)));

    /// <summary>Name of a page folder without its order prefix, in lower case - <c>1.cover</c> is <c>cover</c>.</summary>
    public static string NameOfFolder(string? path)
    {
        var trimmed = Normalize(path).TrimEnd('/');
        var name = trimmed.Length == 0 ? string.Empty : trimmed[(trimmed.LastIndexOf('/') + 1)..];

        return WithoutOrder(name);
    }

    /// <summary>Name of a page as the author sees it, for example <c>Title page</c>.</summary>
    public static string DisplayNameOfFile(string? path) => NameOfFile(path) switch
    {
        "title" => "Title page",
        "copyright" or "copy" => "Copyright page",
        "contents" or "toc" => "Contents",
        "publisher" or "imprint" => "Publisher page",
        "dedicate" or "dedication" => "Dedication",
        var name when IsBlankName(name) => "Blank page",
        "foreword" or "forward" or "preface" => "Foreword",
        "index" => "Index",
        "appendix" or "annex" => "Appendix",
        "blurb" or "about" => "Blurb",
        "front" => "Front cover",
        "back" => "Back cover",
        var name when name.Length > 0 => char.ToUpperInvariant(name[0]) + name[1..],
        _ => "Page"
    };

    /// <summary>
    /// Whether a page is a sheet kept blank - <c>blank</c>, <c>empty</c>, and the numbered ones
    /// <c>blank-2</c> and <c>empty-3</c> - so a spread can be filled without writing a design for it.
    /// </summary>
    public static bool IsBlankName(string? name)
    {
        var plain = WithoutOrder(Path.GetFileNameWithoutExtension(Normalize(name)));

        return plain is "blank" or "empty"
            || plain.StartsWith("blank-", StringComparison.Ordinal)
            || plain.StartsWith("empty-", StringComparison.Ordinal);
    }

    /// <summary>Whether a page is a blank page: one whose file is kept under a name this app reads as blank.</summary>
    public static bool IsBlank(BookPageFile? file) => file is not null && IsBlankName(file.FilePath);

    /// <summary>The designs a part of the book is made of, in the order they print.</summary>
    public static IReadOnlyList<string> DesignNamesOf(PageGroupRole role) => role switch
    {
        PageGroupRole.Blurb => ["blurb"],
        PageGroupRole.Publisher => ["title", "publisher", "dedicate", "copyright", "foreword"],
        PageGroupRole.Appendix => ["appendix"],
        _ => []
    };

    /// <summary>
    /// The designs of a part of the book a new book is given - the ones the book prints without being
    /// asked. The other designs of a part are optional: a dedication, a copyright page or a foreword
    /// is designed when the author wants it, so it is never written ahead of them and never prints
    /// blank.
    /// </summary>
    public static IReadOnlyList<string> StarterNamesOf(PageGroupRole role) => role switch
    {
        PageGroupRole.Blurb => ["blurb"],
        PageGroupRole.Publisher => ["title", "publisher"],
        PageGroupRole.Appendix => ["appendix"],
        _ => []
    };

    private static string WithoutOrder(string? name)
    {
        var trimmed = (name ?? string.Empty).Trim();
        var start = 0;

        while (start < trimmed.Length && char.IsDigit(trimmed[start]))
        {
            start++;
        }

        if (start > 0 && start < trimmed.Length && trimmed[start] is '.' or '-' or '_' or ' ')
        {
            while (start < trimmed.Length && trimmed[start] is '.' or '-' or '_' or ' ')
            {
                start++;
            }
        }
        else if (start == trimmed.Length)
        {
            start = 0;
        }

        return trimmed[start..].Trim().ToLowerInvariant();
    }
}
