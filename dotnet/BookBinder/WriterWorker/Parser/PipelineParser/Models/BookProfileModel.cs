using System.Text.Json;
using System.Text.Json.Serialization;

using WriterWorker.Ctl;
using WriterWorker.Models;

namespace WriterWorker.Parser.PipelineParser.Models;

/// <summary>
/// The <c>profile.json</c> of a book folder: everything the publisher adds to a book - the paper,
/// the font, the footer, the covers and the designed pages that open and close it - and the source
/// its content is printed from. The file sits next to the content of the book, in
/// <c>profile/publish/&lt;profile&gt;</c>, so the source stays portable: a book moved to another
/// machine prints the same way, and the master copy it was cloned from is kept in
/// <c>writer/.framework/templates/profile/publish</c>. What the author wrote - the name, language,
/// form and parser of the content - is never described here; it belongs to the pipeline state of the
/// book, so printing and writing stay apart.
/// <para>
/// A profile is cascaded: the framework template is cloned into the pipeline of a book, and the
/// pipeline's profile travels into each published version. The <c>source</c> section says which of
/// those folders the content comes from, so a profile that is read on its own - the copy inside a
/// published edition, or one shared with a printer - still finds the <c>book.json</c> of the book and
/// follows it into its chapters and segments.
/// </para>
/// </summary>
internal sealed class BookProfileModel
{
    /// <summary>
    /// Version of the file this build writes. Version 2 dropped the <c>content</c> section a profile
    /// used to carry, so the file holds the publisher side of the book and nothing else; version 3
    /// added the <c>source</c> section that records where the content is printed from.
    /// </summary>
    public const int CurrentVersion = 3;

    [JsonPropertyName("version")]
    public int Version { get; set; } = CurrentVersion;

    /// <summary>
    /// Name of the profile, which is the folder it is kept in - <c>default</c>, or the binding and
    /// paper the profile prints with when the book has more than one.
    /// </summary>
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    /// <summary>The book source the profile prints its content from.</summary>
    [JsonPropertyName("source")]
    public BookProfileSourceModel? Source { get; set; }

    /// <summary>The publisher side of the book: its details, its page setup and its page folders.</summary>
    [JsonPropertyName("book")]
    public BookProfileBookModel? Book { get; set; }

    /// <summary>Keys a newer profile carries are kept when this app writes the file back.</summary>
    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}

/// <summary>
/// The source a profile prints its content from: the book it belongs to, whether that book is still
/// being written or was published, the folder of the workspace it sits in, and - for a published
/// edition - the version folder that was printed. The book itself is read from there - its
/// <c>book.json</c>, then its chapters and their segments - so the profile never carries content of
/// its own and a book and its print setup can be copied apart.
/// </summary>
internal sealed class BookProfileSourceModel
{
    /// <summary>Name of the book the profile prints, for example <c>nouka</c>.</summary>
    [JsonPropertyName("book_name")]
    public string? BookName { get; set; }

    /// <summary>
    /// Kind of source the content comes from - <c>pipeline</c> while the book is being written, or
    /// <c>published</c> for an edition that was published.
    /// </summary>
    [JsonPropertyName("source_format")]
    public string? SourceFormat { get; set; }

    /// <summary>Folder of the book source, relative to the workspace folder of its format.</summary>
    [JsonPropertyName("source_path")]
    public string? SourcePath { get; set; }

    /// <summary>Number of the published version the profile prints; null while the book is in the pipeline.</summary>
    [JsonPropertyName("version")]
    public int? Version { get; set; }

    /// <summary>A deep copy, so a caller can edit a source without touching the one it read.</summary>
    public BookProfileSourceModel Copy() => new()
    {
        BookName = BookName,
        SourceFormat = SourceFormat,
        SourcePath = SourcePath,
        Version = Version
    };
}

/// <summary>
/// The publisher side of a book: the publishing details of the edition, the page setup it prints
/// with and the page folders it prints in order. The details are the same object the Book Model tab
/// edits, so a profile and a book describe an edition the same way. Every file the profile points at
/// - the covers, the background and the publisher's logo - is recorded relative to the folder the
/// profile is kept in, so the source stays portable.
/// </summary>
internal sealed class BookProfileBookModel : BookMetadata
{
    /// <summary>Paper, font, footer, background, layout and covers of the export.</summary>
    [JsonPropertyName("options")]
    public PdfExportOptions? Options { get; set; }

    /// <summary>
    /// The page folders the book prints - <c>pages/cover</c>, <c>pages/blurb</c>, <c>pages/publisher</c>,
    /// … - in print order, each with the format of the pages it holds and the pages themselves in the
    /// order they print. The publisher specific folders come from the profile; the content folders
    /// stay empty and print what the author wrote.
    /// </summary>
    [JsonPropertyName("pages")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public List<BookConfigPageModel>? Pages { get; set; }

    /// <summary>A deep copy, so a caller can edit a profile without touching the one it read.</summary>
    public BookProfileBookModel Copy()
    {
        var copy = new BookProfileBookModel { Options = (Options ?? new()).Clone() };

        copy.CopyFrom(this);
        copy.Pages = Pages?.Select(page => new BookConfigPageModel
        {
            Order = page.Order,
            FilePath = page.FilePath,
            Format = page.Format,
            Paths = page.Paths?
                .Select(file => new BookConfigPageFileModel
                {
                    Order = file.Order,
                    FilePath = file.FilePath,
                    ContentType = file.ContentType
                })
                .ToList(),
            AdditionalProperties = page.AdditionalProperties
        }).ToList();

        return copy;
    }

    /// <inheritdoc />
    public override BookMetadata Clone() => Copy();
}
