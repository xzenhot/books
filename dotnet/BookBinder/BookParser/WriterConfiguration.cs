using System;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;


using WriterWorker.Parser.PipelineParser.Models;

namespace WriterWorker.Configuration;

/// <summary>
/// Reads and writes the <c>config.json</c> of a book folder: the file the writer pipeline keeps the
/// title, language, chapter/segment inventory and publish counters in, and where this app stores the
/// <c>printing</c> section so a book is printed the same way every time. Keys the pipeline adds later
/// are kept on round-trip, and a file that cannot be parsed is copied to <c>config.json.bak</c>
/// before a new one is written.
/// </summary>
public static class WriterConfiguration
{
    public const string FileName = "config.json";

    /// <summary>Name of the copy kept when a configuration cannot be parsed.</summary>
    public const string BackupSuffix = ".bak";

    /// <summary>Name the layout section is written under.</summary>
    public const string PrintingSection = "printing";

    /// <summary>Name an older configuration used for the layout section.</summary>
    public const string LegacyPrintingSection = "layout";

    /// <summary>Name the publishing details are written under.</summary>
    public const string BookSection = "overriden";

    /// <summary>Name an older configuration used for the publishing details.</summary>
    public const string LegacyBookSection = "book";

    private static readonly JsonSerializerOptions FileOptions = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true,

        // The model names its own keys; the policy only shapes the printing section, which the
        // pipeline file spells in snake_case too (page_width_mm, font_family, …).
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        Converters = { new JsonStringEnumConverter() }
    };

    /// <summary>Path of the configuration of the book in <paramref name="bookFolder"/>.</summary>
    public static string PathIn(string bookFolder) => Path.Combine(ConfigFolder(bookFolder), FileName);

    /// <summary>
    /// Folder whose <c>config.json</c> describes the book in <paramref name="bookFolder"/>: the folder
    /// itself, or the newest version folder of a published book, because a published edition keeps
    /// every file of the book - the configuration included - inside its version folders.
    /// </summary>
    public static string ConfigFolder(string bookFolder)
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

    /// <summary>
    /// Reads the configuration of <paramref name="bookFolder"/>; null when the folder has none or
    /// the file cannot be parsed.
    /// </summary>
    public static BookConfigModel? Load(string? bookFolder)
    {
        if (string.IsNullOrWhiteSpace(bookFolder))
        {
            return null;
        }

        return LoadFile(PathIn(Path.GetFullPath(bookFolder)));
    }

    /// <summary>Reads a book configuration file; null when it is missing or cannot be parsed.</summary>
    public static BookConfigModel? LoadFile(string? path)
    {
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
        {
            return null;
        }

        try
        {
            var config = JsonSerializer.Deserialize<BookConfigModel>(File.ReadAllText(path), FileOptions);
            return config is null ? null : AdoptLegacySections(config);
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
    /// Moves a section written under its older name (<c>layout</c>, <c>book</c>) onto the property the
    /// model reads, so a file written before the rename is still understood and is rewritten under
    /// the current names.
    /// </summary>
    private static BookConfigModel AdoptLegacySections(BookConfigModel config)
    {
        if (config.AdditionalProperties is not { } extra)
        {
            return config;
        }

        if (config.Layout is null && Take(extra, LegacyPrintingSection) is { } layout)
        {
            config.Layout = layout.Deserialize<BookLayout>(FileOptions);
        }

        if (config.Book is null && Take(extra, LegacyBookSection) is { } book)
        {
            config.Book = book.Deserialize<WriterWorker.Models.BookMetadata>(FileOptions);
        }

        return config;

        static JsonElement? Take(Dictionary<string, JsonElement> extra, string key)
        {
            if (!extra.TryGetValue(key, out var value))
            {
                return null;
            }

            extra.Remove(key);
            return value;
        }
    }

    /// <summary>
    /// Reads the configuration of <paramref name="bookFolder"/> to write it back: a missing file
    /// gives an empty configuration and an unreadable one is backed up first.
    /// </summary>
    public static BookConfigModel Read(string bookFolder)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);

        var path = PathIn(Path.GetFullPath(bookFolder));
        if (!File.Exists(path))
        {
            return new BookConfigModel();
        }

        if (LoadFile(path) is { } config)
        {
            return config;
        }

        try
        {
            File.Copy(path, path + BackupSuffix, overwrite: true);
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException)
        {
        }

        return new BookConfigModel();
    }

    /// <summary>Writes <paramref name="config"/> to <c>config.json</c> in <paramref name="bookFolder"/>.</summary>
    public static void Save(string bookFolder, BookConfigModel config)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);
        ArgumentNullException.ThrowIfNull(config);

        var folder = Path.GetFullPath(bookFolder);
        Directory.CreateDirectory(folder);
        File.WriteAllText(PathIn(folder), JsonSerializer.Serialize(config, FileOptions));
    }
}
