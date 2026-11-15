using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

using WriterWorker.Controller;
using WriterWorker.Ctl;
using WriterWorker.Models;
using WriterWorker.Parser.PipelineParser.Models;
using WriterWorker.Parser.PublishedParser.Contents;

namespace WriterWorker.Configuration;

/// <summary>
/// Reads and writes the print profile of a book - the publisher side of it: its details, the paper,
/// font, footer and covers it prints with, and the page folders it prints in order. The profile is
/// kept in the source of the book, at <c>profile/publish/default/profile.json</c>, with the pages it
/// points at beside it in <c>profile/publish/default/pages</c>, so the source of a book stays
/// portable and the print setup never shares a file with what the pipeline writes. The author's
/// chapters never come from the profile; they are read from the folders of the workspace.
/// <para>
/// The profile is the only record of the print setup. A book that still keeps its setup in the
/// <c>display</c>, <c>overriden</c>, <c>pages</c> or <c>profile</c> sections of a <c>config.json</c>
/// is moved onto a profile the first time it is read, and those sections are removed from
/// <c>config.json</c> so the pipeline state and the print setup stop sharing one file. A
/// <c>profile.json</c> or a <c>pages</c> folder left at the root of the source by an older version is
/// moved into the profile folder the same way.
/// </para>
/// </summary>
internal static class BookProfile
{
    public const string FileName = "profile.json";

    /// <summary>Name of the copy kept when a profile cannot be parsed.</summary>
    public const string BackupSuffix = ".bak";

    /// <summary>
    /// Folder of the print profile, inside the source of the book: the profile travels with the
    /// content, so a source copied to another machine prints the same book.
    /// </summary>
    public const string FolderName = "profile";

    /// <summary>Folder of the profiles a book can be printed with, inside <see cref="FolderName"/>.</summary>
    public const string PublishFolderName = "publish";

    /// <summary>Version of the profile this build writes.</summary>
    public const int CurrentVersion = BookProfileModel.CurrentVersion;

    /// <summary>Profile a book is set up from when it names none.</summary>
    public const string DefaultName = "default";

    /// <summary>Object of the file that holds the publisher side of the book.</summary>
    public const string BookSection = "book";

    /// <summary>Object of <see cref="BookSection"/> that holds the page setup.</summary>
    public const string OptionsSection = "options";

    /// <summary>Array of <see cref="BookSection"/> that holds the page folders.</summary>
    public const string PagesSection = "pages";

    /// <summary>
    /// Section a profile written before version 2 carried: the name, language, form and parser of the
    /// content, which is what the pipeline records about the author's writing rather than how the book
    /// prints. It is dropped when an older profile is read.
    /// </summary>
    public const string ContentSection = "content";

    /// <summary>Object of the file that records the source the content is printed from.</summary>
    public const string SourceSection = "source";

    /// <summary>Kind of source a book that is still being written has.</summary>
    public const string PipelineFormat = "pipeline";

    /// <summary>Kind of source a book that was published has.</summary>
    public const string PublishedFormat = "published";

    private static readonly JsonSerializerOptions FileOptions = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true,

        // The models name their own keys where the file spells them differently; the policy covers
        // the details and the page setup, which the profile writes in snake_case (display_name,
        // page_width_mm, …).
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        Converters = { new JsonStringEnumConverter() }
    };

    /// <summary>
    /// Folder whose <c>profile.json</c> describes the book in <paramref name="bookFolder"/>: the
    /// folder itself, or the newest version folder of a published book, because a published edition
    /// keeps every file of the book - its profile included - inside its version folders.
    /// </summary>
    public static string FolderOf(string bookFolder)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);

        var folder = Path.GetFullPath(bookFolder);

        try
        {
            return BookParsers.For(folder)?.Resolve(folder) is { Length: > 0 } resolved
                ? Path.GetFullPath(resolved)
                : folder;
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or ArgumentException
            or NotSupportedException)
        {
            return folder;
        }
    }

    /// <summary>Path of the profile of the book in <paramref name="bookFolder"/>.</summary>
    public static string PathIn(string bookFolder) => Path.Combine(ProfileFolderOf(bookFolder), FileName);

    /// <summary>Folder the profiles of the book in <paramref name="bookFolder"/> are kept in.</summary>
    public static string ProfilesFolderIn(string bookFolder) =>
        Path.Combine(FolderOf(bookFolder), FolderName, PublishFolderName);

    /// <summary>Folder of the profile named <paramref name="name"/> in <paramref name="bookFolder"/>.</summary>
    public static string ProfileFolderFor(string bookFolder, string? name) =>
        Path.Combine(ProfilesFolderIn(bookFolder), string.IsNullOrWhiteSpace(name) ? DefaultName : name.Trim());

    /// <summary>
    /// Folder of the profile the book in <paramref name="bookFolder"/> prints with:
    /// <c>profile/publish/default</c> of its source, or the profile it keeps instead when the book
    /// has no <c>default</c> one.
    /// </summary>
    public static string ProfileFolderOf(string bookFolder)
    {
        var root = ProfilesFolderIn(bookFolder);
        var standard = Path.Combine(root, DefaultName);

        if (File.Exists(Path.Combine(standard, FileName)))
        {
            return standard;
        }

        try
        {
            if (Directory.Exists(root))
            {
                var other = Directory.EnumerateDirectories(root)
                    .Where(folder => File.Exists(Path.Combine(folder, FileName)))
                    .OrderBy(Path.GetFileName, StringComparer.OrdinalIgnoreCase)
                    .FirstOrDefault();

                if (other is not null)
                {
                    return other;
                }
            }
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException)
        {
        }

        return standard;
    }

    /// <summary>Folder the pages of the profile of <paramref name="bookFolder"/> are kept in.</summary>
    public static string PagesFolderIn(string bookFolder) =>
        Path.Combine(ProfileFolderOf(bookFolder), BookPages.FolderName);

    /// <summary>
    /// Moves the print files an older version kept beside the content of the book into the profile
    /// folder of its source: a <c>profile.json</c> and a <c>pages</c> folder at the root of the book
    /// become <c>profile/publish/default/profile.json</c> and <c>profile/publish/default/pages</c>, so
    /// the print setup of a book lives in one place instead of being mixed with what the author
    /// wrote. Returns whether anything moved.
    /// </summary>
    public static bool MigrateLegacyLayout(string bookFolder)
    {
        if (string.IsNullOrWhiteSpace(bookFolder))
        {
            return false;
        }

        string source;
        string target;

        try
        {
            source = FolderOf(Path.GetFullPath(bookFolder));
            target = ProfileFolderOf(source);
        }
        catch (Exception exception) when (exception is ArgumentException
            or NotSupportedException
            or IOException)
        {
            return false;
        }

        if (string.Equals(source, target, StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        var moved = false;

        foreach (var legacy in (string[])[Path.Combine(source, FileName), Path.Combine(source, FileName + BackupSuffix)])
        {
            if (!File.Exists(legacy))
            {
                continue;
            }

            try
            {
                var destination = Path.Combine(target, Path.GetFileName(legacy));

                if (!File.Exists(destination))
                {
                    Directory.CreateDirectory(target);
                    File.Move(legacy, destination);
                }
                else
                {
                    File.Delete(legacy);
                }

                moved = true;
            }
            catch (Exception exception) when (exception is IOException
                or UnauthorizedAccessException
                or NotSupportedException)
            {
            }
        }

        return MovePages(Path.Combine(source, BookPages.FolderName), Path.Combine(target, BookPages.FolderName)) || moved;
    }

    /// <summary>Moves the files of a <c>pages</c> folder kept at the root of the book into the profile, leaving a file that is already there.</summary>
    private static bool MovePages(string source, string target)
    {
        if (!Directory.Exists(source))
        {
            return false;
        }

        var moved = false;

        try
        {
            foreach (var path in Directory.EnumerateFiles(source, "*", SearchOption.AllDirectories))
            {
                var destination = Path.Combine(target, Path.GetRelativePath(source, path));

                Directory.CreateDirectory(Path.GetDirectoryName(destination)!);

                if (File.Exists(destination))
                {
                    File.Delete(path);
                }
                else
                {
                    File.Move(path, destination);
                }

                moved = true;
            }

            foreach (var folder in Directory.EnumerateDirectories(source, "*", SearchOption.AllDirectories)
                .OrderByDescending(path => path.Length))
            {
                if (!Directory.EnumerateFileSystemEntries(folder).Any())
                {
                    Directory.Delete(folder);
                }
            }

            if (!Directory.EnumerateFileSystemEntries(source).Any())
            {
                Directory.Delete(source);
            }
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException)
        {
        }

        return moved;
    }

    /// <summary>
    /// Reads the profile of <paramref name="bookFolder"/>; null when the book has none yet. A book
    /// that still keeps its setup in <c>config.json</c> is moved onto a profile on the first read.
    /// </summary>
    public static BookProfileModel? Load(string? bookFolder)
    {
        if (string.IsNullOrWhiteSpace(bookFolder))
        {
            return null;
        }

        var folder = FolderOf(Path.GetFullPath(bookFolder));

        MigrateLegacyLayout(folder);

        var path = PathIn(folder);

        if (File.Exists(path))
        {
            return LoadFile(path);
        }

        return Migrate(folder);
    }

    /// <summary>Reads a profile file; null when it is missing or cannot be parsed.</summary>
    public static BookProfileModel? LoadFile(string? path)
    {
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
        {
            return null;
        }

        try
        {
            return Normalize(JsonSerializer.Deserialize<BookProfileModel>(File.ReadAllText(path), FileOptions));
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or JsonException
            or NotSupportedException)
        {
            return null;
        }
    }

    /// <summary>
    /// Reads the profile of <paramref name="bookFolder"/> to write it back: a book without a profile
    /// gives an empty one - after its legacy <c>config.json</c> sections have been moved onto a
    /// profile - and a profile that cannot be parsed is backed up first.
    /// </summary>
    public static BookProfileModel Read(string bookFolder)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);

        var folder = FolderOf(Path.GetFullPath(bookFolder));

        MigrateLegacyLayout(folder);

        var path = PathIn(folder);

        if (Load(folder) is { } profile)
        {
            return profile;
        }

        if (File.Exists(path))
        {
            try
            {
                File.Copy(path, path + BackupSuffix, overwrite: true);
            }
            catch (Exception exception) when (exception is IOException
                or UnauthorizedAccessException
                or NotSupportedException)
            {
            }
        }

        return Normalize(new BookProfileModel())!;
    }

    /// <summary>Writes <paramref name="profile"/> as the <c>profile.json</c> of <paramref name="bookFolder"/>.</summary>
    public static void Save(string bookFolder, BookProfileModel profile)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);
        ArgumentNullException.ThrowIfNull(profile);

        var book = FolderOf(Path.GetFullPath(bookFolder));
        var folder = ProfileFolderOf(book);

        // A profile written into a book records where that book's content is printed from, so the copy
        // that travels into a published edition can still be followed back to its source.
        profile.Source ??= SourceOf(book);

        Directory.CreateDirectory(folder);
        File.WriteAllText(Path.Combine(folder, FileName), JsonSerializer.Serialize(Normalize(profile), FileOptions));
    }

    /// <summary>Serialises <paramref name="profile"/> the way the file holds it.</summary>
    public static string ToJson(BookProfileModel profile) =>
        JsonSerializer.Serialize(Normalize(profile), FileOptions);

    /// <summary>Reads a profile from JSON; null when the text is not a profile.</summary>
    public static BookProfileModel? FromJson(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return null;
        }

        try
        {
            return Normalize(JsonSerializer.Deserialize<BookProfileModel>(json, FileOptions));
        }
        catch (Exception exception) when (exception is JsonException or NotSupportedException)
        {
            return null;
        }
    }

    /// <summary>The publisher side of <paramref name="profile"/>, created when the file has none.</summary>
    public static BookProfileBookModel BookOf(BookProfileModel profile)
    {
        ArgumentNullException.ThrowIfNull(profile);

        return profile.Book ??= new BookProfileBookModel();
    }

    /// <summary>Name of the profile, the default one when the file names none.</summary>
    public static string NameOf(BookProfileModel? profile) =>
        string.IsNullOrWhiteSpace(profile?.Name) ? DefaultName : profile!.Name!.Trim();

    /// <summary>Name of the profile the book in <paramref name="bookFolder"/> was set up from.</summary>
    public static string? RecordedName(string? bookFolder) =>
        Load(bookFolder) is { } profile ? NameOf(profile) : null;

    /// <summary>
    /// The source the book in <paramref name="bookFolder"/> prints its content from, as a profile
    /// records it in its <c>source</c> section: the pipeline folder the book is being written in, or
    /// the version folder it was published as. Null when the folder is not a book folder.
    /// </summary>
    public static BookProfileSourceModel? SourceOf(string? bookFolder)
    {
        if (string.IsNullOrWhiteSpace(bookFolder))
        {
            return null;
        }

        string folder;

        try
        {
            folder = FolderOf(Path.GetFullPath(bookFolder));
        }
        catch (Exception exception) when (exception is ArgumentException
            or NotSupportedException
            or IOException)
        {
            return null;
        }

        var name = Path.GetFileName(folder.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));

        if (string.IsNullOrEmpty(name))
        {
            return null;
        }

        // A published edition keeps every file of the book - its profile included - inside its version
        // folder, so the book it prints is the folder above it and the version is the number it carries.
        var version = PublishedVersion.ParseNumber(name);
        var published = version > 0 && PublishedVersion.IsVersionFolder(folder);
        var sourceFolder = published ? Path.GetDirectoryName(folder) : folder;
        var book = sourceFolder is null ? null : Path.GetFileName(sourceFolder);

        if (sourceFolder is null || string.IsNullOrEmpty(book))
        {
            return null;
        }

        var format = published ? PublishedFormat : PipelineFormat;

        return new BookProfileSourceModel
        {
            BookName = book,
            SourceFormat = format,
            SourcePath = RelativeToFormatRoot(sourceFolder, format) ?? book,
            Version = published ? version : null
        };
    }

    /// <summary>
    /// The folder the content of the book in <paramref name="bookFolder"/> comes from, read from the
    /// <c>source</c> section of its profile: the pipeline folder the book is written in, or the version
    /// folder it was published as. A profile read on its own - the copy inside a published edition, or
    /// one shared with a printer - still finds the <c>book.json</c> of its book from there. Null when
    /// the profile records no source or the folder it names is gone.
    /// </summary>
    public static string? ContentFolderOf(string? bookFolder)
    {
        if (Load(bookFolder)?.Source is not { } source)
        {
            return null;
        }

        var format = Text(source.SourceFormat) ?? PipelineFormat;
        var path = Text(source.SourcePath) ?? Text(source.BookName);

        if (path is null)
        {
            return null;
        }

        try
        {
            var profileFolder = ProfileFolderOf(FolderOf(Path.GetFullPath(bookFolder!)));
            var root = FormatRootOf(profileFolder, format);

            if (root is null)
            {
                return null;
            }

            var folder = Path.GetFullPath(Path.Combine(root, path.Replace('/', Path.DirectorySeparatorChar)));

            if (source.Version is { } version)
            {
                folder = VersionFolderIn(folder, version) ?? folder;
            }

            return IsBookSource(folder) ? folder : null;
        }
        catch (Exception exception) when (exception is ArgumentException
            or NotSupportedException
            or IOException)
        {
            return null;
        }
    }

    /// <summary>The publishing details the profile of <paramref name="bookFolder"/> keeps.</summary>
    public static BookMetadata? Metadata(string? bookFolder) => Load(bookFolder)?.Book?.Clone().Normalize();

    /// <summary>
    /// The page setup the profile of <paramref name="bookFolder"/> keeps, wrapped as a layout named
    /// after the profile; null when the book has no profile.
    /// </summary>
    public static BookLayout? Layout(string? bookFolder)
    {
        if (Load(bookFolder) is not { } profile)
        {
            return null;
        }

        var options = profile.Book?.Options?.Clone() ?? new PdfExportOptions();
        options.Normalize();

        return new BookLayout
        {
            Name = NameOf(profile),
            Options = options
        };
    }

    /// <summary>
    /// Writes the page setup of <paramref name="layout"/> - and, when <paramref name="book"/> is
    /// given, the publishing details of the edition - into the profile of
    /// <paramref name="bookFolder"/>. Everything else the profile holds, the page folders included, is
    /// written back unchanged. A logo kept inside the book is recorded relative to the profile, so the
    /// source stays portable.
    /// </summary>
    public static void SaveLayout(string bookFolder, BookLayout layout, BookMetadata? book)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);
        ArgumentNullException.ThrowIfNull(layout);

        var profile = Read(bookFolder);

        if (!string.IsNullOrWhiteSpace(layout.Name))
        {
            profile.Name = layout.Name.Trim();
        }

        var details = BookOf(profile);
        details.Options = layout.Options.Clone();

        if (book is not null)
        {
            details.CopyFrom(RelativePaths(bookFolder, book.Clone().Normalize()));
        }

        Save(bookFolder, profile);
    }

    /// <summary>
    /// The page setup with the file paths a profile keeps relative to its own folder made absolute,
    /// so a portable profile can be used by an export that reads files from the folder.
    /// </summary>
    public static PdfExportOptions ResolvedPaths(string? bookFolder, PdfExportOptions options)
    {
        var resolved = options.Clone();

        resolved.FrontCoverImagePath = Absolute(bookFolder, options.FrontCoverImagePath);
        resolved.BackCoverImagePath = Absolute(bookFolder, options.BackCoverImagePath);
        resolved.BackgroundImagePath = Absolute(bookFolder, options.BackgroundImagePath);

        return resolved;
    }

    /// <summary>
    /// The publishing details with the logo a profile keeps relative to its own folder made absolute,
    /// so a portable profile can be used by an export that reads files from the folder.
    /// </summary>
    public static BookMetadata? ResolvedPaths(string? bookFolder, BookMetadata? book)
    {
        if (book is null)
        {
            return null;
        }

        var resolved = book.Clone();
        resolved.PublisherLogoPath = Absolute(bookFolder, book.PublisherLogoPath);

        return resolved;
    }

    /// <summary>
    /// The page setup with the file paths inside <paramref name="bookFolder"/> written relative to it,
    /// so a profile stays portable when it is copied to another machine.
    /// </summary>
    public static PdfExportOptions RelativePaths(string? bookFolder, PdfExportOptions options)
    {
        var relative = options.Clone();

        relative.FrontCoverImagePath = Inside(bookFolder, options.FrontCoverImagePath);
        relative.BackCoverImagePath = Inside(bookFolder, options.BackCoverImagePath);
        relative.BackgroundImagePath = Inside(bookFolder, options.BackgroundImagePath);

        return relative;
    }

    /// <summary>
    /// The publishing details with the logo inside <paramref name="bookFolder"/> written relative to
    /// it, so a profile stays portable when it is copied to another machine. A logo kept outside the
    /// book - the one picked from another folder of the machine - stays absolute.
    /// </summary>
    public static BookMetadata? RelativePaths(string? bookFolder, BookMetadata? book)
    {
        if (book is null)
        {
            return null;
        }

        var relative = book.Clone();
        relative.PublisherLogoPath = Inside(bookFolder, book.PublisherLogoPath);

        return relative;
    }

    /// <summary>Fills in what a hand-edited or older profile may leave out.</summary>
    public static BookProfileModel? Normalize(BookProfileModel? profile)
    {
        if (profile is null)
        {
            return null;
        }

        if (profile.Version < CurrentVersion)
        {
            // A profile older than this build still described the author's content. The print profile
            // holds the publisher side of the book only, so that section is dropped instead of being
            // written back as an unknown key. A profile written before version 3 also carried no source
            // section; it is filled in from the book folder the next time the profile is written.
            Drop(profile.AdditionalProperties, ContentSection);
            profile.Version = CurrentVersion;
        }

        profile.Version = profile.Version <= 0 ? CurrentVersion : profile.Version;
        profile.Name = Text(profile.Name) ?? DefaultName;

        if (profile.Source is { } source
            && (Text(source.BookName) is not null || Text(source.SourcePath) is not null))
        {
            source.BookName = Text(source.BookName) ?? Text(source.SourcePath);
            source.SourcePath = Text(source.SourcePath) ?? source.BookName;
            source.SourceFormat = Text(source.SourceFormat) ?? PipelineFormat;
        }

        profile.Book ??= new BookProfileBookModel();
        profile.Book.Options ??= new PdfExportOptions();
        profile.Book.Options.Normalize();
        profile.Book.Normalize();
        profile.Book.Pages ??= [];

        foreach (var page in profile.Book.Pages)
        {
            var role = BookPages.RoleOf(page.FilePath);
            var format = string.IsNullOrWhiteSpace(page.Format)
                ? BookPages.FormatOf(role)
                : BookPages.ParseFormat(page.Format);

            page.Format = BookPages.FormatName(format);

            foreach (var file in page.Paths ?? [])
            {
                if (string.IsNullOrWhiteSpace(file.ContentType) && !string.IsNullOrWhiteSpace(file.FilePath))
                {
                    file.ContentType = BookPages.ContentTypeOf(file.FilePath, format);
                }
                else if (file.ContentType is { } contentType)
                {
                    file.ContentType = contentType.Trim();
                }
            }
        }

        return profile;
    }

    /// <summary>Removes <paramref name="key"/> from the keys a profile kept although this build does not model them.</summary>
    private static void Drop(Dictionary<string, JsonElement>? additional, string key)
    {
        if (additional is null)
        {
            return;
        }

        foreach (var name in additional.Keys.Where(name => string.Equals(name, key, StringComparison.OrdinalIgnoreCase)).ToList())
        {
            additional.Remove(name);
        }
    }

    private static string? Absolute(string? bookFolder, string? path)
    {
        var trimmed = Text(path);

        if (trimmed is null || Path.IsPathRooted(trimmed))
        {
            return trimmed;
        }

        return bookFolder is null
            ? trimmed
            : BookPages.Resolve(ProfileFolderOf(Path.GetFullPath(bookFolder)), trimmed) ?? trimmed;
    }

    private static string? Inside(string? bookFolder, string? path)
    {
        var trimmed = Text(path);

        if (trimmed is null || bookFolder is null || !Path.IsPathRooted(trimmed))
        {
            return trimmed;
        }

        try
        {
            var folder = ProfileFolderOf(Path.GetFullPath(bookFolder));
            var relative = Path.GetRelativePath(folder, Path.GetFullPath(trimmed));

            return relative.StartsWith("..", StringComparison.Ordinal)
                ? trimmed
                : relative.Replace('\\', '/');
        }
        catch (Exception exception) when (exception is ArgumentException
            or NotSupportedException
            or IOException)
        {
            return trimmed;
        }
    }

    private static string? Text(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim();

    /// <summary>
    /// Path of <paramref name="folder"/> relative to the workspace folder of
    /// <paramref name="format"/> - <c>workspaces/pipeline</c> or <c>workspaces/published</c> - so a
    /// source stays valid when the workspace is moved to another machine. Null when the folder is not
    /// inside a workspace of that format.
    /// </summary>
    private static string? RelativeToFormatRoot(string folder, string format)
    {
        for (var parent = Path.GetDirectoryName(folder); parent is not null; parent = Path.GetDirectoryName(parent))
        {
            if (string.Equals(Path.GetFileName(parent), format, StringComparison.OrdinalIgnoreCase))
            {
                return Path.GetRelativePath(parent, folder).Replace('\\', '/');
            }
        }

        return null;
    }

    /// <summary>
    /// Folder the sources of <paramref name="format"/> are kept in, found from the folder a profile
    /// sits in: the nearest folder of that name above it, or the folder of that name inside the nearest
    /// <c>workspaces</c> folder. Null when neither is there.
    /// </summary>
    private static string? FormatRootOf(string folder, string format)
    {
        string? workspaces = null;

        for (var parent = folder; parent is not null; parent = Path.GetDirectoryName(parent))
        {
            var name = Path.GetFileName(parent);

            if (string.Equals(name, format, StringComparison.OrdinalIgnoreCase))
            {
                return parent;
            }

            if (workspaces is null && string.Equals(name, "workspaces", StringComparison.OrdinalIgnoreCase))
            {
                workspaces = parent;
            }
        }

        if (workspaces is null)
        {
            return null;
        }

        var candidate = Path.Combine(workspaces, format);

        return Directory.Exists(candidate) ? candidate : null;
    }

    /// <summary>Folder of version <paramref name="version"/> of a published book, in either naming the publisher uses.</summary>
    private static string? VersionFolderIn(string bookFolder, int version)
    {
        foreach (var name in (string[])[$"version{version}", version.ToString(System.Globalization.CultureInfo.InvariantCulture)])
        {
            var candidate = Path.Combine(bookFolder, name);

            if (Directory.Exists(candidate))
            {
                return candidate;
            }
        }

        return null;
    }

    /// <summary>A folder that holds the content of a book: its plan, its chapters or a published edition.</summary>
    private static bool IsBookSource(string folder) =>
        Directory.Exists(folder)
        && (File.Exists(Path.Combine(folder, "book.json"))
            || Directory.Exists(Path.Combine(folder, "chapters"))
            || File.Exists(Path.Combine(folder, "manifest.json"))
            || File.Exists(Path.Combine(folder, "book.md")));

    /// <summary>
    /// Moves a book that still keeps its print setup in the <c>config.json</c> of
    /// <paramref name="folder"/> onto a <c>profile.json</c>: the setup, the publishing details, the
    /// page folders and the name of the profile become a profile, and those sections are removed
    /// from <c>config.json</c> so the file keeps only what the pipeline writes. Null when the
    /// configuration carries no print data, in which case no profile is written.
    /// </summary>
    private static BookProfileModel? Migrate(string folder)
    {
        if (WriterConfiguration.Load(folder) is not { } config)
        {
            return null;
        }

        if (config.Layout is null && config.Book is null && config.Pages is null && config.Profile is null)
        {
            return null;
        }

        var profile = Normalize(new BookProfileModel
        {
            Name = config.Profile,
            Book = new BookProfileBookModel
            {
                Options = config.Layout?.Options,
                Pages = config.Pages
            }
        })!;

        profile.Book!.CopyFrom(config.Book);

        try
        {
            Save(folder, profile);
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException
            or ArgumentException)
        {
            return profile;
        }

        WriterConfiguration.RemovePrintSections(folder);

        return profile;
    }
}
