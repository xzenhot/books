using System;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

using WriterWorker.Ctl;
using WriterWorker.Models;
using WriterWorker.Parser.PipelineParser.Models;

namespace WriterWorker.Configuration;

/// <summary>
/// One saved book layout: the name it is stored under, when it was written and the page setup it
/// prints with. The wrapper exists so a layout is a single object that can be written to a file or
/// kept in a list, and so further settings can be added later without changing the stores that
/// hold <see cref="BookLayout"/> values. A layout can also live inside the <c>profile.json</c> of a
/// book folder as the page setup of its publisher profile (see <see cref="SaveToBook"/>).
/// </summary>
public sealed class BookLayout
{
    /// <summary>Version of the file layout written by this build.</summary>
    public const int CurrentVersion = 1;

    /// <summary>File dialog filter for layouts saved to disk.</summary>
    public const string FileFilter = "Book layout (*.json)|*.json|All files (*.*)|*.*";

    private static readonly JsonSerializerOptions FileOptions = new()
    {
        WriteIndented = true,
        Converters = { new JsonStringEnumConverter() }
    };

    /// <summary>File layout version; a file written by a newer build is still read.</summary>
    public int Version { get; set; } = CurrentVersion;

    /// <summary>Name the layout is listed under.</summary>
    public string Name { get; set; } = string.Empty;

    /// <summary>Free text about the layout, such as the book it was made for.</summary>
    public string? Description { get; set; }

    /// <summary>When the layout was last written.</summary>
    public DateTimeOffset SavedAt { get; set; } = DateTimeOffset.Now;

    /// <summary>Paper, font, footer, background, layout and covers of the export.</summary>
    public PdfExportOptions Options { get; set; } = new();


    /// <summary>
    /// Wraps <paramref name="options"/> as a layout named <paramref name="name"/>. The book title
    /// and author belong to one export, so they are not part of a reusable layout.
    /// </summary>
    public static BookLayout Create(string name, PdfExportOptions options, string? description = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(name);
        ArgumentNullException.ThrowIfNull(options);

        var saved = options.Clone();
        saved.Title = null;
        saved.Author = null;

        return new BookLayout
        {
            Name = name.Trim(),
            Description = string.IsNullOrWhiteSpace(description) ? null : description.Trim(),
            SavedAt = DateTimeOffset.Now,
            Options = saved
        };
    }

    /// <summary>A deep copy, so a caller can edit a loaded layout without touching the original.</summary>
    public BookLayout Clone() => new()
    {
        Version = Version,
        Name = Name,
        Description = Description,
        SavedAt = SavedAt,
        Options = Options.Clone()
    };

    /// <summary>Writes the layout to <paramref name="path"/> as JSON, creating the folder.</summary>
    public void Save(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        SavedAt = DateTimeOffset.Now;

        var folder = Path.GetDirectoryName(Path.GetFullPath(path));
        if (!string.IsNullOrEmpty(folder))
        {
            Directory.CreateDirectory(folder);
        }

        File.WriteAllText(path, ToJson());
    }

    /// <summary>
    /// Reads the layout stored at <paramref name="path"/>; null when the file is missing or is not
    /// a layout.
    /// </summary>
    public static BookLayout? Load(string? path)
    {
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
        {
            return null;
        }

        try
        {
            return FromJson(File.ReadAllText(path));
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException)
        {
            return null;
        }
    }

    public string ToJson() => JsonSerializer.Serialize(this, FileOptions);

    /// <summary>Reads a layout from JSON; null when the text is not a layout.</summary>
    public static BookLayout? FromJson(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return null;
        }

        try
        {
            return Normalize(JsonSerializer.Deserialize<BookLayout>(json, FileOptions));
        }
        catch (Exception exception) when (exception is JsonException or NotSupportedException)
        {
            return null;
        }
    }

    /// <summary>Path of the profile of the book in <paramref name="bookFolder"/>.</summary>
    public static string BookProfilePath(string bookFolder) => BookProfile.PathIn(bookFolder);

    /// <summary>
    /// Folder that holds the files of the book in <paramref name="bookFolder"/>: the folder itself, or
    /// the newest version folder of a published book, whose designs, pages and profile all live
    /// inside the version.
    /// </summary>
    public static string BookFileFolder(string bookFolder) => BookProfile.FolderOf(bookFolder);

    /// <summary>
    /// Reads the layout kept in the <c>profile.json</c> of <paramref name="bookFolder"/>; null when
    /// the folder has no profile or the profile carries no page setup yet.
    /// </summary>
    public static BookLayout? LoadFromBook(string? bookFolder) => Normalize(BookProfile.Layout(bookFolder));

    /// <summary>Reads the layout from a book <c>profile.json</c> file; null when it has none.</summary>
    public static BookLayout? LoadFromBookFile(string? path)
    {
        if (BookProfile.LoadFile(path) is not { } profile)
        {
            return null;
        }

        var options = profile.Book?.Options?.Clone() ?? new PdfExportOptions();
        options.Normalize();

        return Normalize(new BookLayout { Name = BookProfile.NameOf(profile), Options = options });
    }

    /// <summary>
    /// Merges the layout into the <c>profile.json</c> of <paramref name="bookFolder"/>: everything
    /// the profile keeps - the publishing details and the page folders - is written back unchanged
    /// and only the page setup is replaced, so one file describes how the book prints. A published
    /// book folder has no file of its own, so the newest version folder is written to instead. A
    /// profile that cannot be parsed is kept as <c>profile.json.bak</c> before a new one is written.
    /// </summary>
    public void SaveToBook(string bookFolder) => SaveToBook(bookFolder, null);

    /// <summary>
    /// Writes the layout and, when <paramref name="book"/> is given, the publishing details of the
    /// book into the <c>profile.json</c> of <paramref name="bookFolder"/> in one pass. A null
    /// <paramref name="book"/> keeps the details already stored in the file. The name of the layout is
    /// the name of the profile, so a layout that names none keeps the name the profile already has.
    /// </summary>
    public void SaveToBook(string bookFolder, BookMetadata? book)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);

        var folder = Path.GetFullPath(bookFolder);

        SavedAt = DateTimeOffset.Now;
        BookProfile.SaveLayout(folder, this, book);
    }

    /// <summary>
    /// Reads the publishing details kept in the <c>book</c> object of the <c>profile.json</c> of
    /// <paramref name="bookFolder"/>; null when the folder has no profile or no details yet.
    /// </summary>
    public static BookMetadata? LoadBook(string? bookFolder) => BookProfile.Metadata(bookFolder);

    /// <summary>
    /// Name of the book in <paramref name="bookFolder"/>: the title its profile prints it under, then
    /// <c>book_name</c> from its <c>config.json</c>, then its <c>title</c>, then the folder name.
    /// </summary>
    public static string BookName(string bookFolder)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);

        var folder = Path.GetFullPath(bookFolder);

        if (BookProfile.Load(folder)?.Book?.DisplayName is { } displayed && !string.IsNullOrWhiteSpace(displayed))
        {
            return displayed.Trim();
        }

        var config = WriterConfiguration.Load(folder);

        foreach (var name in new[] { config?.BookName, config?.Title })
        {
            if (!string.IsNullOrWhiteSpace(name))
            {
                return name.Trim();
            }
        }

        return Path.GetFileName(folder.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
    }

    /// <summary>Fills in what a hand-edited or older layout may leave out.</summary>
    private static BookLayout? Normalize(BookLayout? config)
    {
        if (config is null)
        {
            return null;
        }

        config.Options ??= new PdfExportOptions();
        config.Options.Normalize();
        config.Name = config.Name?.Trim() ?? string.Empty;
        config.Version = config.Version <= 0 ? CurrentVersion : config.Version;
        return config;
    }

    public override string ToString() => Name;
}
