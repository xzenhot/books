using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;

using WriterWorker.Configuration;
using WriterWorker.Models;
using WriterWorker.Parser.PipelineParser.Models;

namespace WriterWorker.Ctl;

/// <summary>
/// The publisher profiles a book can be printed with, kept as masters in
/// <c>writer/.framework/templates/profile/publish</c> of the writer repository: the copy a book is set
/// up from. A profile is a <c>profile.json</c> and a <c>pages</c> folder - the page folders in print
/// order, the page setup the book prints with, and the covers and designed pages the publisher adds -
/// so a book that is opened for the first time gets the same structure as every other book of its
/// kind. A master can be edited like a book folder: what is changed there is what the next book starts
/// from.
/// <para>
/// A book keeps its own profile inside its source, at <c>profile/publish/default</c>, once it has been
/// set up - customized for it, so the source stays portable - and a change to a master never reaches
/// back into a book that was already set up.
/// </para>
/// </summary>
internal static class ProfileStore
{
    /// <summary>Folder the profiles are kept in, inside the settings folder.</summary>
    public const string FolderName = "profile";

    /// <summary>Profile a book is cloned from when no other one is asked for.</summary>
    public const string DefaultName = BookProfile.DefaultName;

    /// <summary>Image extensions a cover page is looked for with.</summary>
    private static readonly string[] Images =
    [
        ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"
    ];

    /// <summary>Folder of the templates the masters are seeded from, inside the writer repository.</summary>
    private static readonly string[] TemplateFolders = ["writer", ".framework", "templates", FolderName, BookProfile.PublishFolderName];

    /// <summary>
    /// The folder the master profiles are kept in,
    /// <c>writer/.framework/templates/profile/publish</c> of the writer repository.
    /// </summary>
    public static string Folder => RootOf(null) ?? Path.GetFullPath(Path.Combine([.. TemplateFolders]));

    /// <summary>Folder of the profile a book is cloned from when no other one is asked for.</summary>
    public static string DefaultFolder => PathOf(DefaultName);

    /// <summary>Folder of the profile named <paramref name="name"/>; the default profile when it names none.</summary>
    public static string PathOf(string? name) => Path.Combine(Folder, NameOf(name));

    /// <summary>Path of the <c>profile.json</c> of the profile named <paramref name="name"/>.</summary>
    public static string ProfilePathOf(string? name) => Path.Combine(PathOf(name), BookProfile.FileName);

    /// <summary>Path of the <c>pages</c> folder of the profile named <paramref name="name"/>.</summary>
    public static string PagesFolderOf(string? name) => Path.Combine(PathOf(name), BookPages.FolderName);

    /// <summary>The profiles that exist, in alphabetical order.</summary>
    public static IReadOnlyList<string> Names()
    {
        try
        {
            return Directory.Exists(Folder)
                ? Directory.EnumerateDirectories(Folder)
                    .Select(Path.GetFileName)
                    .Where(name => !string.IsNullOrWhiteSpace(name))
                    .Select(name => name!)
                    .OrderBy(name => name, StringComparer.OrdinalIgnoreCase)
                    .ToList()
                : [];
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException)
        {
            return [];
        }
    }

    /// <summary>
    /// The profiles that exist, as the Select Profile tab lists them: what each one says about the
    /// books cloned from it - the author, the book type, the size it prints at and the pages it starts
    /// with - and which one the book in <paramref name="bookFolder"/> was set up from. The default
    /// profile is seeded first when there is none, so the list is never empty.
    /// </summary>
    public static IReadOnlyList<ProfileInfo> Catalog(string? bookFolder = null)
    {
        Ensure(bookFolder: bookFolder);

        var current = Current(bookFolder);

        return Names()
            .Select(name => Describe(name, string.Equals(name, current, StringComparison.OrdinalIgnoreCase)))
            .ToList();
    }

    /// <summary>
    /// Name of the profile the book in <paramref name="bookFolder"/> was set up from; the default
    /// profile when the book has no profile or records none.
    /// </summary>
    public static string Current(string? bookFolder) => NameOf(BookProfile.RecordedName(bookFolder));

    /// <summary>
    /// Makes the profile named <paramref name="name"/> the one the book in <paramref name="bookFolder"/>
    /// is set up from: the master is customized for the book and written into the source as its
    /// <c>profile.json</c>, and the files the book does not have yet - the covers and the publisher
    /// designs of the <c>pages</c> folder, and the logo beside the profile - are copied into it.
    /// Nothing the book already holds is overwritten, so the author's own pages and content are left
    /// alone. Returns whether anything was copied.
    /// </summary>
    public static bool Apply(string bookFolder, string? name)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);

        var profile = NameOf(name);
        var folder = Path.GetFullPath(bookFolder);

        try
        {
            var master = Ensure(profile, folder);
            var source = Path.Combine(master, BookProfile.FileName);

            if (BookProfile.LoadFile(source) is { } read)
            {
                var target = BookProfile.PathIn(folder);
                var customized = Customize(read, folder, profile);

                Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                File.WriteAllText(target, BookProfile.ToJson(customized));
            }
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException
            or ArgumentException)
        {
        }

        return CopyFolder(PathOf(profile), BookProfile.ProfileFolderOf(folder));
    }

    /// <summary>
    /// Makes sure the profile named <paramref name="name"/> exists - the default profile when it names
    /// none - and seeds it from the templates of the writer repository when it does not: its
    /// <c>profile.json</c> and the covers and designs of its <c>pages</c> folder. A profile the
    /// templates know nothing about is written as a new book's structure instead. Returns the folder of
    /// the profile.
    /// </summary>
    public static string Ensure(string? name = null, string? bookFolder = null)
    {
        var profile = NameOf(name);
        var folder = PathOf(profile);

        try
        {
            Directory.CreateDirectory(folder);

            if (!File.Exists(ProfilePathOf(profile)))
            {
                if (TemplateOf(profile, bookFolder) is { } template)
                {
                    CopyFolder(template, folder);
                }

                if (!File.Exists(ProfilePathOf(profile)))
                {
                    File.WriteAllText(ProfilePathOf(profile), BookProfile.ToJson(Starter(profile)));
                }
            }

            foreach (var group in BookPages.DefaultGroups())
            {
                Directory.CreateDirectory(Path.Combine(folder, group.FilePath.Replace('/', Path.DirectorySeparatorChar)));
            }
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException
            or ArgumentException)
        {
        }

        return folder;
    }

    /// <summary>
    /// Gives <paramref name="bookFolder"/> the profile it starts from - the master named
    /// <paramref name="profile"/> customized for the book - when it has no <c>profile.json</c> of its
    /// own, and the files of the master's <c>pages</c> folder when the book has no pages yet. A book
    /// that already has its own profile and pages is left alone, so nothing the author removed comes
    /// back and nothing they wrote is overwritten. Returns whether anything was copied.
    /// </summary>
    public static bool Seed(string bookFolder, string? profile = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);

        var folder = Path.GetFullPath(bookFolder);
        var name = NameOf(profile);
        var source = Path.GetFullPath(Ensure(name, folder));

        if (string.Equals(source, folder, StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        var copied = false;

        if (!File.Exists(BookProfile.PathIn(folder)) && Apply(folder, name))
        {
            copied = true;
        }

        if (PagesAreEmpty(folder) &&
            CopyFolder(Path.Combine(source, BookPages.FolderName), BookProfile.PagesFolderIn(folder)))
        {
            copied = true;
        }

        return copied;
    }

    /// <summary>
    /// What the profile named <paramref name="name"/> says about a book, read from its
    /// <c>profile.json</c>; a profile that has none yet describes the page setup a book starts with.
    /// </summary>
    private static ProfileInfo Describe(string name, bool inUse)
    {
        var profile = BookProfile.LoadFile(ProfilePathOf(name));
        var options = profile?.Book?.Options;

        return new ProfileInfo(
            name,
            profile?.Book?.Author,
            profile?.Book?.CoverType ?? BookCoverType.Paperback,
            options?.PageWidthMm ?? PdfExportOptions.DefaultPageWidthMm,
            options?.PageHeightMm ?? PdfExportOptions.DefaultPageHeightMm,
            profile?.Book?.Pages?.Sum(page => page.Paths?.Count ?? 0) ?? 0,
            inUse);
    }

    /// <summary>
    /// The <c>profile.json</c> a profile starts with when the templates carry none: the page folders of
    /// a new book in print order and the default page setup, so a book cloned from the profile prints
    /// without being set up first.
    /// </summary>
    private static BookProfileModel Starter(string name)
    {
        var position = 0;

        return BookProfile.Normalize(new BookProfileModel
        {
            Name = name,
            Book = new BookProfileBookModel
            {
                Options = new PdfExportOptions(),
                Pages = BookPages.DefaultGroups()
                    .Select(group => new BookConfigPageModel
                    {
                        Order = (++position).ToString(CultureInfo.InvariantCulture),
                        FilePath = group.FilePath,
                        Format = BookPages.FormatName(group.Format),
                        Paths = []
                    })
                    .ToList()
            }
        })!;
    }

    /// <summary>
    /// Customizes a master profile for the book in <paramref name="bookFolder"/>, so the profile written
    /// into the source describes that book: its title and author, a footer made from them, the covers of
    /// its page folder, and a page folder for every part of the book. The designs and the page setup
    /// come from the master unchanged, and nothing about the author's writing is recorded, because a
    /// print profile describes the publisher side of the book only.
    /// </summary>
    private static BookProfileModel Customize(BookProfileModel master, string bookFolder, string name)
    {
        var profile = BookProfile.Normalize(master)!;
        var config = WriterConfiguration.Load(bookFolder);

        profile.Name = name;
        profile.Version = BookProfile.CurrentVersion;

        // The profile travels with the source of the book and into a published edition, so it records
        // the folder the content is printed from and the copy can always be followed back to it.
        profile.Source = BookProfile.SourceOf(bookFolder) ?? profile.Source;

        var book = BookProfile.BookOf(profile);

        // A master names the book it was made for, so the book's own title and author win, and a
        // master that names neither leaves them to the book.
        book.DisplayName = Text(config?.Title) ?? Text(config?.BookName) ?? Text(book.DisplayName);
        book.Author = Text(config?.Book?.Author) ?? Text(book.Author);

        var options = book.Options ??= new PdfExportOptions();
        options.FooterText = Text(options.FooterText) ?? Footer(book);

        // The cover paths of a master name the pages it ships, so they are pointed at the pages of this
        // book instead of at a file of the machine the master was made on. A book that has no cover
        // image yet keeps the paths of the master.
        var (front, back) = Covers(bookFolder);

        if (front is not null)
        {
            options.FrontCoverImagePath = front;
        }

        if (back is not null)
        {
            options.BackCoverImagePath = back;
        }

        book.Pages = Groups(book.Pages);

        return profile;
    }

    /// <summary>The page folders of a profile with every part of the book in it, in print order.</summary>
    private static List<BookConfigPageModel> Groups(List<BookConfigPageModel>? pages)
    {
        var groups = pages ?? [];
        var position = 0;

        foreach (var role in BookPages.Roles)
        {
            var folder = BookPages.FolderPathOf(role);

            if (!groups.Any(group => BookPages.SamePath(group.FilePath, folder)))
            {
                groups.Add(new BookConfigPageModel
                {
                    Order = BookPages.DefaultOrderOf(role).ToString(CultureInfo.InvariantCulture),
                    FilePath = folder,
                    Format = BookPages.FormatName(BookPages.FormatOf(role)),
                    Paths = []
                });
            }
        }

        var ordered = groups.OrderBy(group => OrderOf(group.Order)).ToList();

        foreach (var group in ordered)
        {
            group.Order = (++position).ToString(CultureInfo.InvariantCulture);
            group.FilePath = BookPages.Normalize(group.FilePath).TrimEnd('/') + "/";
            group.Format = Text(group.Format) ?? BookPages.FormatName(BookPages.FormatOf(BookPages.RoleOf(group.FilePath)));
        }

        return ordered;
    }

    /// <summary>The copyright line of a book, made from its author and the year it was produced.</summary>
    private static string Footer(BookMetadata book)
    {
        var year = book.YearOfProduction ?? DateTime.Now.Year;
        var author = Text(book.Author) ?? Text(book.DisplayName);

        return author is null
            ? $"© {year}. All rights reserved."
            : $"© {year} {author}. All rights reserved.";
    }

    /// <summary>
    /// The cover images of the book in <paramref name="bookFolder"/> as paths relative to the folder:
    /// the file named <c>front</c> and the file named <c>back</c> of <c>pages/cover</c>, falling back to
    /// the first image of the folder for the front cover.
    /// </summary>
    private static (string? Front, string? Back) Covers(string bookFolder)
    {
        var baseFolder = BookProfile.ProfileFolderOf(bookFolder);
        var folder = Path.Combine(BookProfile.PagesFolderIn(bookFolder), BookPages.NameOfRole(PageGroupRole.Cover));

        try
        {
            if (!Directory.Exists(folder))
            {
                return (null, null);
            }

            var images = Directory.EnumerateFiles(folder)
                .Where(path => Images.Contains(Path.GetExtension(path), StringComparer.OrdinalIgnoreCase))
                .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                .ToList();

            string? Named(string name) => images.FirstOrDefault(path =>
                string.Equals(Path.GetFileNameWithoutExtension(path), name, StringComparison.OrdinalIgnoreCase));

            return (Relative(baseFolder, Named("front") ?? images.FirstOrDefault()), Relative(baseFolder, Named("back")));
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException)
        {
            return (null, null);
        }
    }

    /// <summary>
    /// The folder of the template the profile named <paramref name="name"/> is seeded from: the one of
    /// that name in the writer repository, the default template when it has no folder of its own, or
    /// null when the repository is not reachable from the book, the app or the current folder.
    /// </summary>
    private static string? TemplateOf(string name, string? bookFolder)
    {
        foreach (var root in Roots(bookFolder))
        {
            var folder = Path.Combine(root, name);

            if (File.Exists(Path.Combine(folder, BookProfile.FileName)))
            {
                return folder;
            }

            var fallback = Path.Combine(root, DefaultName);

            if (File.Exists(Path.Combine(fallback, BookProfile.FileName)))
            {
                return fallback;
            }
        }

        return null;
    }

    /// <summary>Folder the masters are kept in, the first template folder of the writer repository that exists.</summary>
    private static string? RootOf(string? bookFolder) => Roots(bookFolder).FirstOrDefault();

    /// <summary>The template folders of the writer repository, nearest first.</summary>
    private static IEnumerable<string> Roots(string? bookFolder)
    {
        string?[] starts = [bookFolder, AppContext.BaseDirectory, Directory.GetCurrentDirectory()];

        foreach (var start in starts)
        {
            if (string.IsNullOrWhiteSpace(start))
            {
                continue;
            }

            DirectoryInfo? folder;

            try
            {
                folder = new DirectoryInfo(Path.GetFullPath(start));
            }
            catch (Exception exception) when (exception is ArgumentException or NotSupportedException)
            {
                continue;
            }

            for (; folder is not null; folder = folder.Parent)
            {
                var candidate = Path.Combine([folder.FullName, .. TemplateFolders]);

                if (Directory.Exists(candidate))
                {
                    yield return candidate;
                }
            }
        }
    }

    /// <summary>Whether the book in <paramref name="bookFolder"/> holds no page file at all yet.</summary>
    private static bool PagesAreEmpty(string bookFolder)
    {
        var pages = BookProfile.PagesFolderIn(bookFolder);

        try
        {
            return !Directory.Exists(pages)
                || !Directory.EnumerateFiles(pages, "*", SearchOption.AllDirectories).Any();
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException)
        {
            return false;
        }
    }

    /// <summary>
    /// Copies the folders and files of <paramref name="source"/> into <paramref name="target"/>, leaving
    /// a file that is already there untouched. Returns whether anything was copied.
    /// </summary>
    private static bool CopyFolder(string source, string target)
    {
        if (!Directory.Exists(source))
        {
            return false;
        }

        var copied = false;

        try
        {
            foreach (var path in Directory.EnumerateDirectories(source, "*", SearchOption.AllDirectories))
            {
                Directory.CreateDirectory(Path.Combine(target, Path.GetRelativePath(source, path)));
            }

            foreach (var path in Directory.EnumerateFiles(source, "*", SearchOption.AllDirectories))
            {
                var destination = Path.Combine(target, Path.GetRelativePath(source, path));

                if (File.Exists(destination))
                {
                    continue;
                }

                Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
                File.Copy(path, destination);
                copied = true;
            }
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException
            or ArgumentException)
        {
        }

        return copied;
    }

    private static string? Relative(string bookFolder, string? path) =>
        path is null ? null : BookPages.Relative(bookFolder, path);

    private static string? Text(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim();

    private static int OrderOf(string? order) =>
        int.TryParse(order, NumberStyles.Integer, CultureInfo.InvariantCulture, out var number) ? number : int.MaxValue;

    /// <summary>The name of a profile as a folder name, the default profile when it names none.</summary>
    private static string NameOf(string? name)
    {
        var trimmed = (name ?? string.Empty).Trim();

        if (trimmed.Length == 0)
        {
            return DefaultName;
        }

        var invalid = Path.GetInvalidFileNameChars();
        var clean = new string(trimmed
            .Where(character => character != '/' && character != '\\' && !invalid.Contains(character))
            .ToArray())
            .Trim();

        return clean.Length == 0 ? DefaultName : clean;
    }
}

/// <summary>
/// What a profile says about the books cloned from it - the author, the book type and the size the book
/// prints at, and the pages it starts with - so the Select Profile tab can list a profile by what it is
/// for instead of by its folder name alone.
/// </summary>
internal sealed class ProfileInfo
{
    public ProfileInfo(
        string name,
        string? author,
        BookCoverType coverType,
        double widthMm,
        double heightMm,
        int pages,
        bool inUse)
    {
        Name = name;
        Author = string.IsNullOrWhiteSpace(author) ? null : author.Trim();
        BookType = coverType == BookCoverType.HardCover ? "Hard cover" : "Paperback";
        Size = $"{Number(widthMm)} x {Number(heightMm)} mm";
        Pages = pages;
        InUse = inUse;
        Details = string.Join(
            " - ",
            Author ?? "No author",
            BookType,
            Size,
            pages == 1 ? "1 page" : $"{pages} pages");
        State = inUse ? "In use" : string.Empty;
    }

    /// <summary>Name of the profile, which is also the name of its folder.</summary>
    public string Name { get; }

    /// <summary>Author the profile was made for; null when it names none.</summary>
    public string? Author { get; }

    /// <summary>Binding the profile prints for, paperback or hard cover.</summary>
    public string BookType { get; }

    /// <summary>Trim size of the profile, such as <c>215.9 x 139.7 mm</c>.</summary>
    public string Size { get; }

    /// <summary>Number of pages the profile starts a book with.</summary>
    public int Pages { get; }

    /// <summary>Whether the book at hand was set up from this profile.</summary>
    public bool InUse { get; }

    /// <summary>One line naming the author, the book type, the size and the pages of the profile.</summary>
    public string Details { get; }

    /// <summary><c>In use</c> for the profile of the book at hand, empty for the others.</summary>
    public string State { get; }

    /// <summary>Whether this is the profile a book is set up from when no other one is chosen.</summary>
    public bool IsDefault =>
        string.Equals(Name, ProfileStore.DefaultName, StringComparison.OrdinalIgnoreCase);

    private static string Number(double value) => value.ToString("0.#", CultureInfo.InvariantCulture);
}