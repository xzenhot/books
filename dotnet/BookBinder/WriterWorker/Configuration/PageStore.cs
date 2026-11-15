using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Documents;
using System.Windows.Media;

using WriterWorker.Ctl;
using WriterWorker.Models;
using WriterWorker.Parser.PipelineParser.Models;
using WriterWorker.Parser.PublishedParser.Contents;

namespace WriterWorker.Configuration;

/// <summary>
/// The pages of a book, kept in the page folders of its workspace and recorded in the <c>pages</c>
/// array of the <c>book</c> object of its <c>profile.json</c>: the folders in print order -
/// <c>pages/cover</c>, <c>pages/blurb</c>, <c>pages/publisher</c>, <c>pages/index</c>,
/// <c>pages/content</c>, <c>pages/appendix</c>, <c>pages/backcover</c> - each with the format of the
/// pages it holds and the pages themselves in
/// the order they print. There is no other record of the pages: the covers, the designed pages, the
/// generated index, the chapters and the appendix are all part of the same sequence, so this is the
/// one structure the export, the setup window and the designer read and write. A page folder or a
/// file that still carries the order prefix of an older version - <c>pages/3.publisher</c>,
/// <c>1.title.rtf</c> - is renamed after what it holds, and a design an older version left in the
/// <c>layout</c> folder is moved into the folder of its part.
/// </summary>
internal static class PageStore
{
    private const string BodyFont = "Georgia";

    private static readonly string[] ImageExtensions =
    [
        ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"
    ];

    private static readonly string[] MarkdownExtensions = [".md", ".markdown", ".txt"];

    private static readonly Regex OrderPrefix = new(@"^(\d+)", RegexOptions.CultureInvariant);

    /// <summary>
    /// Folder the page folders of the book in <paramref name="bookFolder"/> are kept in: the
    /// <c>pages</c> folder of its print profile, inside the source of the book.
    /// </summary>
    public static string FolderIn(string bookFolder)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);
        return BookProfile.PagesFolderIn(bookFolder);
    }

    /// <summary>
    /// Folder a page path of the profile is recorded against: the folder the profile sits in, so
    /// <c>pages/cover/front.jpg</c> names a file of the profile and not of the workspace.
    /// </summary>
    private static string BaseOf(string bookFolder) => BookProfile.ProfileFolderOf(bookFolder);

    /// <summary>
    /// The page folders of <paramref name="bookFolder"/> in print order, as its <c>profile.json</c>
    /// records them. A book whose profile records no pages is read from the folders it has, so
    /// a workspace the app has not written yet still prints.
    /// </summary>
    public static IReadOnlyList<BookPageGroup> Load(string? bookFolder)
    {
        if (string.IsNullOrWhiteSpace(bookFolder))
        {
            return [];
        }

        var folder = Path.GetFullPath(bookFolder);

        BookProfile.MigrateLegacyLayout(folder);

        return BookPages.Ordered(ReadGroups(folder));
    }

    /// <summary>
    /// The page folder of <paramref name="role"/> in <paramref name="bookFolder"/>, or null when the
    /// book has none.
    /// </summary>
    public static BookPageGroup? GroupOf(string? bookFolder, PageGroupRole role) =>
        Load(bookFolder).FirstOrDefault(group => group.Role == role);

    /// <summary>
    /// Gives <paramref name="bookFolder"/> the page structure the export prints: the folders that
    /// still carry the order prefix of an older version are renamed, the designs left in the
    /// <c>layout</c> folder are moved into their page folder, the parts of the book it does not have
    /// yet are added in print order, and the pages every book must have - the title page and the
    /// publisher page - are written with starter content built from <paramref name="book"/>. What the
    /// author removed stays removed: the files of a folder are only taken from disk when the folder
    /// records none. The configuration is written back when anything changed.
    /// </summary>
    public static IReadOnlyList<BookPageGroup> Ensure(string bookFolder, BookMetadata? book = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);

        var folder = Path.GetFullPath(bookFolder);
        var changed = false;

        BookProfile.MigrateLegacyLayout(folder);

        Directory.CreateDirectory(FolderIn(folder));

        // A book that has never been set up starts from the profile it records - the default profile
        // of the settings folder when it records none - which is where the structure and the starter
        // designs are kept instead of the workspace.
        if (ProfileStore.Seed(folder, ProfileStore.Current(folder)))
        {
            changed = true;
        }

        var movedFolders = StripFolderPrefixes(folder);
        var movedFiles = StripOrderPrefixes(folder);

        if (movedFolders.Count > 0 || movedFiles.Count > 0)
        {
            RewritePaths(folder, movedFolders, movedFiles);
            changed = true;
        }

        if (MigrateLegacyDesigns(folder) > 0)
        {
            changed = true;
        }

        var groups = ReadGroups(folder).Select(group => group.Clone()).ToList();

        // A published edition is a finished copy, so it is read as it is instead of being given the
        // folders of a book that is still being made.
        var published = PublishedVersion.IsVersionFolder(folder);

        foreach (var role in BookPages.Roles)
        {
            var group = groups.FirstOrDefault(candidate => candidate.Role == role);

            if (group is null)
            {
                group = new BookPageGroup
                {
                    Order = BookPages.DefaultOrderOf(role),
                    FilePath = BookPages.FolderPathOf(role),
                    Format = BookPages.FormatOf(role),
                    Files = FilesIn(folder, BookPages.FolderPathOf(role), BookPages.FormatOf(role))
                };

                groups.Add(group);
                changed = true;
            }

            // Every part of the book keeps its folder, so an image or a design can be put in it
            // without the author making the folder first.
            if (!published && BookPages.Resolve(BaseOf(folder), group.FilePath) is { } groupFolder)
            {
                Directory.CreateDirectory(groupFolder);
            }

            if (group.Files.Count > 0)
            {
                continue;
            }

            var found = FilesIn(folder, group.FilePath, group.Format);
            if (found.Count > 0)
            {
                group.Files = found;
                changed = true;
            }
        }

        if (EnsureMandatoryPages(folder, groups, book))
        {
            changed = true;
        }

        var ordered = BookPages.Ordered(groups);

        if (changed)
        {
            Save(folder, ordered);
        }

        return ordered;
    }

    /// <summary>
    /// Makes sure the pages every book prints - the title page and the publisher page - are designed:
    /// a missing page is added to the publisher folder as <c>title.rtf</c> or <c>publisher.rtf</c>,
    /// ahead of the other publisher pages, and a page recorded without its file is written with
    /// starter content.
    /// </summary>
    private static bool EnsureMandatoryPages(string bookFolder, List<BookPageGroup> groups, BookMetadata? book)
    {
        if (groups.FirstOrDefault(group => group.Role == PageGroupRole.Publisher) is not { } publisher)
        {
            return false;
        }

        var changed = false;
        var position = 0;

        foreach (var name in (string[])["title", "publisher"])
        {
            position++;

            if (publisher.Files.FirstOrDefault(file => string.Equals(file.Name, name, StringComparison.OrdinalIgnoreCase)) is { } listed)
            {
                if (BookPages.Resolve(BaseOf(bookFolder), listed.FilePath) is { } path && !File.Exists(path))
                {
                    WriteStarter(bookFolder, path, name, book);
                    changed = true;
                }

                continue;
            }

            var relative = publisher.FilePath + name + BookPages.RtfExtension;
            var design = BookPages.Resolve(BaseOf(bookFolder), relative);

            if (design is not null)
            {
                WriteStarter(bookFolder, design, name, book);
            }

            publisher.Files.Insert(Math.Min(position - 1, publisher.Files.Count), new BookPageFile
            {
                Order = position,
                FilePath = relative,
                ContentType = BookPages.RtfContentType
            });

            changed = true;
        }

        return changed;
    }

    /// <summary>
    /// Writes <paramref name="groups"/> into the <c>pages</c> array of the <c>book</c> object of the
    /// <c>profile.json</c> of <paramref name="bookFolder"/>: the folders in print order, each with its
    /// format and its pages in the order they print. Everything else the profile holds - the
    /// publishing details, the page setup and the content identity - is written back unchanged.
    /// </summary>
    public static void Save(string bookFolder, IEnumerable<BookPageGroup> groups)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);
        ArgumentNullException.ThrowIfNull(groups);

        var folder = Path.GetFullPath(bookFolder);
        var profile = BookProfile.Read(folder);
        var ordered = BookPages.Ordered(groups.Select(group => group.Clone().Rank())).ToList();

        profile.Book ??= new BookProfileBookModel();
        profile.Book.Pages = [];

        var position = 0;

        foreach (var group in ordered)
        {
            profile.Book.Pages.Add(new BookConfigPageModel
            {
                Order = (++position).ToString(CultureInfo.InvariantCulture),
                FilePath = FolderKey(group.FilePath),
                Format = BookPages.FormatName(group.Format),
                Paths = group.Printed
                    .Select((file, index) => new BookConfigPageFileModel
                    {
                        Order = (index + 1).ToString(CultureInfo.InvariantCulture),
                        FilePath = BookPages.Normalize(file.FilePath),
                        ContentType = BookPages.ContentTypeOf(file, group.Format)
                    })
                    .ToList()
            });
        }

        BookProfile.Save(folder, profile);
    }

    /// <summary>
    /// Adds <paramref name="relativePath"/> to the pages of <paramref name="role"/> at the end of the
    /// folder, so a page the author designs is printed as soon as it exists.
    /// </summary>
    public static IReadOnlyList<BookPageGroup> AddFile(string bookFolder, PageGroupRole role, string relativePath)
    {
        var folder = Path.GetFullPath(bookFolder);
        var groups = ReadGroups(folder).Select(group => group.Clone()).ToList();
        var group = groups.FirstOrDefault(candidate => candidate.Role == role);

        if (group is null)
        {
            group = new BookPageGroup
            {
                Order = BookPages.DefaultOrderOf(role),
                FilePath = BookPages.FolderPathOf(role),
                Format = BookPages.FormatOf(role)
            };

            groups.Add(group);
        }

        group.Add(relativePath);
        group.Rank();
        Save(folder, groups);

        return BookPages.Ordered(groups);
    }

    /// <summary>
    /// The cover images of <paramref name="bookFolder"/>: the file named <c>front</c> and the file
    /// named <c>back</c>, falling back to the first image of the cover folder for the front cover and
    /// to the first page of the back cover folder for the back one.
    /// </summary>
    public static (string? Front, string? Back) Covers(string? bookFolder)
    {
        var files = (GroupOf(bookFolder, PageGroupRole.Cover)?.Printed ?? Enumerable.Empty<BookPageFile>())
            .Select(file => (file.Name, Path: BookPages.Resolve(bookFolder is null ? null : BaseOf(bookFolder), file.FilePath)))
            .Where(file => file.Path is not null && File.Exists(file.Path))
            .ToList();

        var front = files.FirstOrDefault(file => file.Name == "front").Path
            ?? files.FirstOrDefault(file => file.Name != "back").Path;

        var back = FirstImage(bookFolder, PageGroupRole.BackCover)
            ?? files.FirstOrDefault(file => file.Name == "back").Path;

        return (front, back);
    }

    /// <summary>The first image of the pages of <paramref name="role"/>, so a part kept in its own folder can stand in for a cover.</summary>
    private static string? FirstImage(string? bookFolder, PageGroupRole role) =>
        GroupOf(bookFolder, role)?.Printed
            .Select(file => BookPages.Resolve(bookFolder is null ? null : BaseOf(bookFolder), file.FilePath))
            .FirstOrDefault(path => path is not null && File.Exists(path));

    /// <summary>
    /// Drops <paramref name="relativePath"/> from the pages of <paramref name="role"/>, leaving the
    /// file on disk, so the page stops printing.
    /// </summary>
    public static IReadOnlyList<BookPageGroup> RemoveFile(string bookFolder, PageGroupRole role, string relativePath)
    {
        var folder = Path.GetFullPath(bookFolder);
        var groups = ReadGroups(folder).Select(group => group.Clone()).ToList();

        if (groups.FirstOrDefault(candidate => candidate.Role == role) is { } group && group.Remove(relativePath))
        {
            Save(folder, groups);
        }

        return BookPages.Ordered(groups);
    }

    /// <summary>
    /// Moves the page <paramref name="relativePath"/> of <paramref name="role"/> one place up
    /// (<paramref name="offset"/> -1) or down (+1) among the pages of its part, and writes the new
    /// order to the configuration, so the order of the list is the order the pages print in. A page
    /// at the top or at the bottom of its part stays where it is.
    /// </summary>
    public static IReadOnlyList<BookPageGroup> MoveFile(
        string bookFolder,
        PageGroupRole role,
        string relativePath,
        int offset)
    {
        var folder = Path.GetFullPath(bookFolder);
        var groups = ReadGroups(folder).Select(group => group.Clone()).ToList();

        if (groups.FirstOrDefault(candidate => candidate.Role == role) is not { } group)
        {
            return BookPages.Ordered(groups);
        }

        var pages = group.Printed.ToList();
        var from = pages.FindIndex(file => BookPages.SamePath(file.FilePath, relativePath));
        var to = from + offset;

        if (from < 0 || to < 0 || to >= pages.Count)
        {
            return BookPages.Ordered(groups);
        }

        (pages[from], pages[to]) = (pages[to], pages[from]);

        Rank(pages);
        Save(folder, groups);

        return BookPages.Ordered(groups);
    }

    /// <summary>
    /// Puts the page <paramref name="relativePath"/> among the pages of <paramref name="role"/> at
    /// <paramref name="position"/> - one for the first page of the part, the count of the pages plus
    /// one for the last - so a page the author adds prints where it was put instead of at the end of
    /// the part.
    /// </summary>
    public static IReadOnlyList<BookPageGroup> InsertFile(
        string bookFolder,
        PageGroupRole role,
        string relativePath,
        int position)
    {
        var folder = Path.GetFullPath(bookFolder);
        var groups = ReadGroups(folder).Select(group => group.Clone()).ToList();
        var group = groups.FirstOrDefault(candidate => candidate.Role == role);

        if (group is null)
        {
            group = new BookPageGroup
            {
                Order = BookPages.DefaultOrderOf(role),
                FilePath = BookPages.FolderPathOf(role),
                Format = BookPages.FormatOf(role)
            };

            groups.Add(group);
        }

        var added = group.Add(relativePath);
        var pages = group.Printed.Where(file => !ReferenceEquals(file, added)).ToList();

        pages.Insert(Math.Clamp(position - 1, 0, pages.Count), added);

        Rank(pages);
        Save(folder, groups);

        return BookPages.Ordered(groups);
    }

    /// <summary>
    /// Deletes the page <paramref name="relativePath"/> of <paramref name="role"/>: it is taken out
    /// of the pages of the book, and its file is deleted from disk unless <paramref name="deleteFile"/>
    /// says otherwise, so a page that was added by mistake does not come back with the next "Create
    /// missing pages".
    /// </summary>
    public static IReadOnlyList<BookPageGroup> DeleteFile(
        string bookFolder,
        PageGroupRole role,
        string relativePath,
        bool deleteFile = true)
    {
        var groups = RemoveFile(bookFolder, role, relativePath);

        if (deleteFile && BookPages.Resolve(BaseOf(bookFolder), relativePath) is { } path && File.Exists(path))
        {
            File.Delete(path);
        }

        return groups;
    }

    /// <summary>
    /// The design <paramref name="role"/> can be given next: the first design of the part the book
    /// does not have yet - the dedication, the copyright page or the foreword of the publisher
    /// pages, the blurb, the appendix - or a numbered page once the part has all of its designs.
    /// </summary>
    public static string NextDesignName(string bookFolder, PageGroupRole role)
    {
        var folder = Path.GetFullPath(bookFolder);
        var group = ReadGroups(folder).FirstOrDefault(candidate => candidate.Role == role);
        var used = (group?.Files ?? []).Select(file => file.Name).ToHashSet(StringComparer.OrdinalIgnoreCase);

        foreach (var name in BookPages.DesignNamesOf(role))
        {
            if (!used.Contains(name))
            {
                return name;
            }
        }

        for (var number = 2; ; number++)
        {
            var name = "page" + number.ToString(CultureInfo.InvariantCulture);

            if (!used.Contains(name))
            {
                return name;
            }
        }
    }

    /// <summary>
    /// Puts a blank page among the pages of <paramref name="role"/> at <paramref name="position"/>:
    /// a design with nothing on it, kept as <c>blank.rtf</c> - <c>blank-2.rtf</c> once the part has
    /// one - so a sheet a spread needs can be filled without a page being written for it. The page
    /// is recorded in the configuration like any other, and prints as an empty sheet.
    /// </summary>
    public static (IReadOnlyList<BookPageGroup> Groups, string RelativePath) InsertBlank(
        string bookFolder,
        PageGroupRole role,
        int position)
    {
        var folder = Path.GetFullPath(bookFolder);
        var relativeFolder = ReadGroups(folder).FirstOrDefault(candidate => candidate.Role == role)?.FilePath
            ?? BookPages.FolderPathOf(role);
        var relative = relativeFolder + NextBlankName(folder, role) + BookPages.RtfExtension;

        if (BookPages.Resolve(BaseOf(folder), relative) is { } path)
        {
            WriteStarter(folder, path, BookPages.BlankName);
        }

        return (InsertFile(folder, role, relative, position), relative);
    }

    /// <summary>Name a blank page of <paramref name="role"/> can be kept under: <c>blank</c>, then <c>blank-2</c>, <c>blank-3</c>.</summary>
    private static string NextBlankName(string bookFolder, PageGroupRole role)
    {
        var group = ReadGroups(bookFolder).FirstOrDefault(candidate => candidate.Role == role);
        var used = (group?.Files ?? []).Select(file => file.Name).ToHashSet(StringComparer.OrdinalIgnoreCase);

        if (!used.Contains(BookPages.BlankName))
        {
            return BookPages.BlankName;
        }

        for (var number = 2; ; number++)
        {
            var name = BookPages.BlankName + "-" + number.ToString(CultureInfo.InvariantCulture);

            if (!used.Contains(name))
            {
                return name;
            }
        }
    }

    /// <summary>Numbers <paramref name="pages"/> from one in the order they are listed.</summary>
    private static void Rank(IReadOnlyList<BookPageFile> pages)
    {
        for (var index = 0; index < pages.Count; index++)
        {
            pages[index].Order = index + 1;
        }
    }

    /// <summary>
    /// Gives <paramref name="bookFolder"/> the designs of <paramref name="role"/> the book prints
    /// without being asked - <c>blurb.rtf</c> for the blurb, <c>title.rtf</c> and
    /// <c>publisher.rtf</c> for the publisher pages, <c>appendix.rtf</c> for the appendix - each
    /// written with starter content built from <paramref name="book"/>. The designs a part may also
    /// have - a dedication, a copyright page, a foreword - are left to the author, and the parts the
    /// export generates, the index and the content, have no designs at all.
    /// </summary>
    public static IReadOnlyList<BookPageGroup> EnsureDesigns(string bookFolder, PageGroupRole role, BookMetadata? book = null)
    {
        var folder = Path.GetFullPath(bookFolder);
        var names = BookPages.StarterNamesOf(role);

        if (names.Count == 0)
        {
            return Load(folder);
        }

        var groups = ReadGroups(folder).Select(group => group.Clone()).ToList();
        var group = groups.FirstOrDefault(candidate => candidate.Role == role);

        if (group is null)
        {
            group = new BookPageGroup
            {
                Order = BookPages.DefaultOrderOf(role),
                FilePath = BookPages.FolderPathOf(role),
                Format = BookPages.FormatOf(role)
            };

            groups.Add(group);
        }

        var changed = false;

        foreach (var name in names)
        {
            if (group.Files.FirstOrDefault(file => string.Equals(file.Name, name, StringComparison.OrdinalIgnoreCase)) is { } listed)
            {
                if (BookPages.Resolve(BaseOf(folder), listed.FilePath) is { } existing && !File.Exists(existing))
                {
                    WriteStarter(folder, existing, name, book);
                    changed = true;
                }

                continue;
            }

            var relative = group.FilePath + name + BookPages.RtfExtension;
            var design = BookPages.Resolve(BaseOf(folder), relative);

            if (design is not null)
            {
                WriteStarter(folder, design, name, book);
            }

            group.Files.Add(new BookPageFile
            {
                Order = group.Files.Count + 1,
                FilePath = relative,
                ContentType = BookPages.RtfContentType
            });
            changed = true;
        }

        if (changed)
        {
            Save(folder, groups);
        }

        return BookPages.Ordered(groups);
    }

    /// <summary>Whether <paramref name="relativePath"/> points into the folder older designs were kept in.</summary>
    public static bool IsLegacy(string? relativePath) =>
        BookPages.Normalize(relativePath).TrimStart('.', '/')
            .StartsWith(BookPages.LegacyFolderName + "/", StringComparison.OrdinalIgnoreCase);

    /// <summary>
    /// Writes a starter design named <paramref name="name"/> to <paramref name="path"/>, leaving an
    /// existing file alone. The document is a WPF object, so this must run on the UI thread.
    /// </summary>
    public static void WriteStarter(string bookFolder, string path, string name, BookMetadata? book = null)
    {
        if (File.Exists(path))
        {
            return;
        }

        var folder = Path.GetDirectoryName(Path.GetFullPath(path));
        if (!string.IsNullOrEmpty(folder))
        {
            Directory.CreateDirectory(folder);
        }

        File.WriteAllText(path, RtfExport.ToRtf(CreateStarterDocument(bookFolder, name, book)));
    }

    /// <summary>
    /// Builds the starter design of the page named <paramref name="name"/> from the publishing
    /// details of the book. It is a plain document the author rewrites in the editor; nothing in the
    /// export depends on its shape.
    /// </summary>
    public static FlowDocument CreateStarterDocument(string bookFolder, string? name, BookMetadata? book = null)
    {
        var document = new FlowDocument
        {
            FontFamily = new FontFamily(BodyFont),
            FontSize = 12,
            PagePadding = new Thickness(0)
        };

        var title = Text(book?.DisplayName) ?? BookLayout.BookName(bookFolder);
        var author = Text(book?.Author);
        var publisher = Text(book?.PublisherName);
        var address = Text(book?.PublisherAddress);
        var copyright = Text(book?.Copyright);
        var isbn = Text(book?.Isbn);
        var about = Text(book?.AboutBook);
        var year = book?.YearOfProduction?.ToString(CultureInfo.InvariantCulture);

        switch (BookPages.NameOfFile(name))
        {
            case "title":
                document.Blocks.Add(Centered(title, 28, bold: true, spaceBefore: 120));
                if (author is not null)
                {
                    document.Blocks.Add(Centered(author, 16, bold: false, spaceBefore: 24));
                }

                if (publisher is not null)
                {
                    document.Blocks.Add(Centered(publisher, 12, bold: false, spaceBefore: 180));
                }

                break;

            case "copyright" or "copy":
                document.Blocks.Add(Centered(copyright ?? $"(c) {year ?? DateTime.Now.Year.ToString(CultureInfo.InvariantCulture)} {author ?? title}", 11));
                if (isbn is not null)
                {
                    document.Blocks.Add(Centered($"ISBN {isbn}", 11, spaceBefore: 12));
                }

                if (publisher is not null)
                {
                    document.Blocks.Add(Centered(publisher, 11, spaceBefore: 12));
                }

                if (address is not null)
                {
                    document.Blocks.Add(Centered(address, 11));
                }

                break;

            case "publisher" or "imprint":
                document.Blocks.Add(Centered(publisher ?? "Publisher", 20, bold: true, spaceBefore: 120));
                if (address is not null)
                {
                    document.Blocks.Add(Centered(address, 12, spaceBefore: 24));
                }

                break;

            case "contents" or "toc" or "index":
                document.Blocks.Add(Centered("Contents", 20, bold: true, spaceBefore: 24));
                document.Blocks.Add(new Paragraph());
                break;

            case "dedicate" or "dedication":
                document.Blocks.Add(Centered(string.Empty, 12, spaceBefore: 160));
                break;

            case "blank" or "empty":
                document.Blocks.Add(new Paragraph());
                break;

            case "foreword" or "forward" or "preface":
                document.Blocks.Add(Centered("Foreword", 20, bold: true, spaceBefore: 24));
                document.Blocks.Add(Centered(publisher is null ? string.Empty : $"by {publisher}", 12, spaceBefore: 8));
                document.Blocks.Add(new Paragraph());
                break;

            case "appendix" or "annex":
                document.Blocks.Add(Centered("Appendix", 20, bold: true, spaceBefore: 24));
                document.Blocks.Add(new Paragraph());
                break;

            case "blurb" or "about":
                if (about is not null)
                {
                    document.Blocks.Add(Centered(about, 13, spaceBefore: 60));
                }
                else
                {
                    document.Blocks.Add(Centered(title, 20, bold: true, spaceBefore: 24));
                    document.Blocks.Add(new Paragraph());
                }

                break;

            default:
                document.Blocks.Add(new Paragraph());
                break;
        }

        return document;
    }

    /// <summary>
    /// Renames the page folders of <paramref name="bookFolder"/> that still carry an order prefix -
    /// <c>pages/3.publisher</c> - to the name of what they hold, <c>pages/publisher</c>, because the
    /// order of the folders is recorded in the configuration. A folder whose new name is taken is
    /// left alone. Returns the folders that moved, with their paths relative to
    /// <paramref name="bookFolder"/>.
    /// </summary>
    public static IReadOnlyList<(string Old, string New)> StripFolderPrefixes(string bookFolder)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);

        var folder = Path.GetFullPath(bookFolder);
        var root = FolderIn(folder);
        var moved = new List<(string Old, string New)>();

        if (!Directory.Exists(root))
        {
            return moved;
        }

        foreach (var source in Directory.EnumerateDirectories(root).OrderBy(path => path, StringComparer.OrdinalIgnoreCase))
        {
            if (PrefixOrderOf(Path.GetFileName(source)) == int.MaxValue)
            {
                continue;
            }

            var target = Path.Combine(root, BookPages.NameOfFolder(source));

            if (Directory.Exists(target) || File.Exists(target))
            {
                continue;
            }

            try
            {
                Directory.Move(source, target);
            }
            catch (Exception exception) when (exception is IOException
                or UnauthorizedAccessException
                or NotSupportedException
                or ArgumentException)
            {
                continue;
            }

            moved.Add((BookPages.Relative(BaseOf(folder), source) + "/", BookPages.Relative(BaseOf(folder), target) + "/"));
        }

        return moved;
    }

    /// <summary>
    /// Renames the files of the page folders of <paramref name="bookFolder"/> that still carry an
    /// order prefix - <c>1.title.rtf</c> - to the name of the page they are, <c>title.rtf</c>,
    /// because the order is recorded in the configuration. A file whose new name is taken is left
    /// alone. Returns the files that moved, with their old and new paths relative to
    /// <paramref name="bookFolder"/>.
    /// </summary>
    public static IReadOnlyList<(string Old, string New)> StripOrderPrefixes(string bookFolder)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);

        var folder = Path.GetFullPath(bookFolder);
        var root = FolderIn(folder);
        var moved = new List<(string Old, string New)>();

        if (!Directory.Exists(root))
        {
            return moved;
        }

        foreach (var source in Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories)
            .OrderBy(path => path, StringComparer.OrdinalIgnoreCase))
        {
            var name = Path.GetFileNameWithoutExtension(source);

            if (PrefixOrderOf(name) == int.MaxValue)
            {
                continue;
            }

            var target = Path.Combine(
                Path.GetDirectoryName(source) ?? root,
                $"{BookPages.NameOfFile(source)}{Path.GetExtension(source)}");

            if (File.Exists(target) || target.Length == 0)
            {
                continue;
            }

            try
            {
                File.Move(source, target);
            }
            catch (Exception exception) when (exception is IOException
                or UnauthorizedAccessException
                or NotSupportedException
                or ArgumentException)
            {
                continue;
            }

            moved.Add((BookPages.Relative(BaseOf(folder), source), BookPages.Relative(BaseOf(folder), target)));
        }

        return moved;
    }

    /// <summary>
    /// Points the <c>pages</c> array of the profile at the folders and files that were renamed, so
    /// nothing keeps pointing at a path that is no longer there.
    /// </summary>
    private static void RewritePaths(
        string bookFolder,
        IReadOnlyList<(string Old, string New)> movedFolders,
        IReadOnlyList<(string Old, string New)> movedFiles)
    {
        if (BookProfile.Load(bookFolder) is not { Book.Pages: { Count: > 0 } pages } profile)
        {
            return;
        }

        foreach (var page in pages)
        {
            page.FilePath = Moved(page.FilePath, movedFolders);

            foreach (var file in page.Paths ?? [])
            {
                file.FilePath = Moved(file.FilePath, movedFiles);
                file.FilePath = Moved(file.FilePath, movedFolders);
            }
        }

        BookProfile.Save(bookFolder, profile);
    }

    private static string? Moved(string? path, IReadOnlyList<(string Old, string New)> moved)
    {
        var relative = BookPages.Normalize(path);

        foreach (var (oldPath, newPath) in moved)
        {
            if (relative.StartsWith(oldPath, StringComparison.OrdinalIgnoreCase))
            {
                return newPath + relative[oldPath.Length..];
            }
        }

        return path;
    }

    /// <summary>
    /// Moves the rich text designs an older version of the app left in the <c>layout</c> folder into
    /// the page folder of the part they belong to - <c>layout/title.rtf</c> becomes
    /// <c>pages/publisher/title.rtf</c> - and removes the folder once it is empty. Anything else the
    /// folder holds is left where it is. Returns how many designs moved.
    /// </summary>
    private static int MigrateLegacyDesigns(string bookFolder)
    {
        var legacy = Path.Combine(bookFolder, BookPages.LegacyFolderName);

        if (!Directory.Exists(legacy))
        {
            return 0;
        }

        var moved = 0;

        foreach (var source in Directory.EnumerateFiles(legacy, "*" + BookPages.RtfExtension)
                     .OrderBy(path => path, StringComparer.OrdinalIgnoreCase))
        {
            var role = LegacyRoleOf(BookPages.NameOfFile(source));
            var target = Path.Combine(
                FolderIn(bookFolder),
                BookPages.NameOfRole(role),
                $"{BookPages.NameOfFile(source)}{Path.GetExtension(source)}");

            if (File.Exists(target))
            {
                continue;
            }

            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                File.Move(source, target);
                moved++;
            }
            catch (Exception exception) when (exception is IOException
                or UnauthorizedAccessException
                or NotSupportedException
                or ArgumentException)
            {
            }
        }

        try
        {
            if (!Directory.EnumerateFileSystemEntries(legacy).Any())
            {
                Directory.Delete(legacy);
            }
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException)
        {
        }

        return moved;
    }

    /// <summary>The part of the book a design of the <c>layout</c> folder belongs to.</summary>
    private static PageGroupRole LegacyRoleOf(string name) => name switch
    {
        "blurb" or "about" => PageGroupRole.Blurb,
        "appendix" or "annex" => PageGroupRole.Appendix,
        "index" => PageGroupRole.Index,
        _ => PageGroupRole.Publisher
    };

    /// <summary>The page folders the profile of <paramref name="bookFolder"/> records, or the ones on disk.</summary>
    private static List<BookPageGroup> ReadGroups(string bookFolder)
    {
        var groups = new List<BookPageGroup>();

        if (BookProfile.Load(bookFolder)?.Book?.Pages is { Count: > 0 } pages)
        {
            foreach (var page in pages.OrderBy(page => OrderOf(page.Order)))
            {
                var path = BookPages.Normalize(page.FilePath);

                if (path.Length == 0)
                {
                    continue;
                }

                var role = BookPages.RoleOf(path);

                groups.Add(new BookPageGroup
                {
                    Order = OrderOf(page.Order) is var order && order != int.MaxValue ? order : BookPages.DefaultOrderOf(role),
                    FilePath = FolderKey(path),
                    Format = string.IsNullOrWhiteSpace(page.Format) ? BookPages.FormatOf(role) : BookPages.ParseFormat(page.Format),
                    Files = (page.Paths ?? [])
                        .OrderBy(file => OrderOf(file.Order))
                        .Select(file => new BookPageFile
                        {
                            Order = OrderOf(file.Order) is var fileOrder && fileOrder != int.MaxValue ? fileOrder : 0,
                            FilePath = BookPages.Normalize(file.FilePath),
                            ContentType = file.ContentType?.Trim() ?? string.Empty
                        })
                        .Where(file => file.FilePath.Length > 0)
                        .ToList()
                });
            }

            return groups;
        }

        var root = FolderIn(bookFolder);
        if (!Directory.Exists(root))
        {
            return groups;
        }

        foreach (var folder in Directory.EnumerateDirectories(root)
            .OrderBy(path => PrefixOrderOf(Path.GetFileName(path)))
            .ThenBy(BookPages.NameOfFolder, StringComparer.OrdinalIgnoreCase))
        {
            var relative = BookPages.Relative(BaseOf(bookFolder), folder) + "/";
            var role = BookPages.RoleOf(relative);

            groups.Add(new BookPageGroup
            {
                Order = BookPages.DefaultOrderOf(role),
                FilePath = relative,
                Format = FormatOf(folder, role),
                Files = FilesIn(bookFolder, relative, FormatOf(folder, role))
            });
        }

        return groups;
    }

    /// <summary>The format of the pages of a folder the configuration says nothing about.</summary>
    private static PageFormat FormatOf(string folder, PageGroupRole role)
    {
        if (role != PageGroupRole.Other)
        {
            return BookPages.FormatOf(role);
        }

        var files = Directory.EnumerateFiles(folder).ToList();

        if (files.Count > 0 && files.All(IsImage))
        {
            return PageFormat.Image;
        }

        if (files.Count > 0 && files.All(IsMarkdown))
        {
            return PageFormat.Markdown;
        }

        return PageFormat.Rtf;
    }

    /// <summary>
    /// The pages a folder holds, in the order their names give them, as paths relative to
    /// <paramref name="bookFolder"/>. Only files of the format of the folder are taken, so an image
    /// kept beside the designs of a folder does not print.
    /// </summary>
    private static List<BookPageFile> FilesIn(string bookFolder, string relativeFolder, PageFormat format)
    {
        var folder = BookPages.Resolve(BaseOf(bookFolder), relativeFolder);

        if (folder is null || !Directory.Exists(folder))
        {
            return [];
        }

        return Directory.EnumerateFiles(folder)
            .Where(path => format switch
            {
                PageFormat.Image => IsImage(path),
                PageFormat.Markdown => IsMarkdown(path),
                _ => IsRtf(path)
            })
            .OrderBy(path => PrefixOrderOf(Path.GetFileNameWithoutExtension(path)))
            .ThenBy(BookPages.NameOfFile, StringComparer.OrdinalIgnoreCase)
            .Select((path, index) => new BookPageFile
            {
                Order = index + 1,
                FilePath = BookPages.Relative(BaseOf(bookFolder), path),
                ContentType = BookPages.ContentTypeOf(path, format)
            })
            .ToList();
    }

    private static bool IsImage(string path) =>
        ImageExtensions.Contains(Path.GetExtension(path), StringComparer.OrdinalIgnoreCase);

    private static bool IsMarkdown(string path) =>
        MarkdownExtensions.Contains(Path.GetExtension(path), StringComparer.OrdinalIgnoreCase);

    private static bool IsRtf(string path) =>
        string.Equals(Path.GetExtension(path), BookPages.RtfExtension, StringComparison.OrdinalIgnoreCase);

    private static Paragraph Centered(string text, double size, bool bold = false, double spaceBefore = 0) => new()
    {
        TextAlignment = TextAlignment.Center,
        FontSize = size,
        FontWeight = bold ? FontWeights.Bold : FontWeights.Normal,
        Margin = new Thickness(0, spaceBefore, 0, 0),
        Inlines = { new Run(text) }
    };

    private static string? Text(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim();

    /// <summary>A page folder or file path of the configuration in the form the file writes it, ending in a slash.</summary>
    private static string FolderKey(string? path)
    {
        var folder = BookPages.Normalize(path).Trim();

        return folder.Length == 0 || folder.EndsWith('/') ? folder : folder + "/";
    }

    private static int OrderOf(string? order) =>
        int.TryParse(order, NumberStyles.Integer, CultureInfo.InvariantCulture, out var number) ? number : int.MaxValue;

    /// <summary>The order prefix of an older name, or <see cref="int.MaxValue"/> when it carries none.</summary>
    private static int PrefixOrderOf(string? name) =>
        name is not null && OrderPrefix.Match(name) is { Success: true } match
            && int.TryParse(match.Groups[1].Value, NumberStyles.Integer, CultureInfo.InvariantCulture, out var order)
                ? order
                : int.MaxValue;
}
