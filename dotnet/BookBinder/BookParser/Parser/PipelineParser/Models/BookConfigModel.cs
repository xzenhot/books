using System.Text.Json;
using System.Text.Json.Serialization;

using WriterWorker.Configuration;

namespace WriterWorker.Parser.PipelineParser.Models;

/// <summary>
/// The <c>config.json</c> of a book folder: the state the writer pipeline keeps between runs -
/// title, language, chapter/segment inventory and publish counters - plus the <c>printing</c>
/// section this app adds so the book is printed the same way every time.
/// </summary>
public sealed class BookConfigModel
{
    [JsonPropertyName("title")]
    public string? Title { get; set; }

    [JsonPropertyName("language")]
    public string? Language { get; set; }

    [JsonPropertyName("context")]
    public string? Context { get; set; }

    [JsonPropertyName("total_chapters")]
    public int TotalChapters { get; set; }

    [JsonPropertyName("completed_chapters")]
    public int CompletedChapters { get; set; }

    /// <summary>Chapter being written, or null when the book is between chapters.</summary>
    [JsonPropertyName("current_chapter")]
    [JsonConverter(typeof(StringOrNumberConverter))]
    public string? CurrentChapter { get; set; }

    [JsonPropertyName("factory")]
    public string? Factory { get; set; }

    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("provider")]
    public string? Provider { get; set; }

    [JsonPropertyName("book_name")]
    public string? BookName { get; set; }

    [JsonPropertyName("form")]
    public string? Form { get; set; }

    [JsonPropertyName("updated_by")]
    public string? UpdatedBy { get; set; }

    [JsonPropertyName("updated_date")]
    public string? UpdatedDate { get; set; }

    [JsonPropertyName("written_chapters")]
    public int WrittenChapters { get; set; }

    [JsonPropertyName("published")]
    public bool Published { get; set; }

    [JsonPropertyName("published_version")]
    public int? PublishedVersion { get; set; }

    [JsonPropertyName("published_at")]
    public string? PublishedAt { get; set; }

    [JsonPropertyName("chapters")]
    public List<BookConfigChapterModel> Chapters { get; set; } = [];

    /// <summary>Paper, font, footer, background, layout and covers of the export.</summary>
    [JsonPropertyName(WriterConfiguration.PrintingSection)]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public BookLayout? Layout { get; set; }

    /// <summary>Display name, author, price, ISBN and publisher of the edition.</summary>
    [JsonPropertyName(WriterConfiguration.BookSection)]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public WriterWorker.Models.BookMetadata? Book { get; set; }

    /// <summary>
    /// The page folders the workspace keeps - <c>pages/cover</c>, <c>pages/blurb</c>, … - in
    /// print order, each with the format of the pages it holds and the pages themselves in the order
    /// they print. This is the only record of the pages of the book: the covers, the designs, the
    /// index, the chapters and the appendix all print from it.
    /// </summary>
    [JsonPropertyName("pages")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public List<BookConfigPageModel>? Pages { get; set; }

    /// <summary>Keys the pipeline adds later are kept when this app writes the file back.</summary>
    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}

/// <summary>
/// One page folder of the workspace as the pipeline records it in <c>config.json</c>:
/// <c>{"order": 3, "file_path": "pages/publisher/", "format": "rtf"}</c>.
/// </summary>
public sealed class BookConfigPageModel
{
    /// <summary>Position of the folder in the book; kept as text because the pipeline writes it as either.</summary>
    [JsonPropertyName("order")]
    [JsonConverter(typeof(StringOrNumberConverter))]
    public string? Order { get; set; }

    [JsonPropertyName("file_path")]
    public string? FilePath { get; set; }

    /// <summary>What the folder holds: <c>image</c>, <c>rtf</c> or <c>markdown</c>.</summary>
    [JsonPropertyName("format")]
    public string? Format { get; set; }

    /// <summary>
    /// The files of the folder in the order they print - <c>{"order": 1, "file_path": "pages/publisher/title.rtf"}</c> -
    /// so the sequence of the book is kept here instead of in the names of the files.
    /// </summary>
    [JsonPropertyName("paths")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public List<BookConfigPageFileModel>? Paths { get; set; }

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}

/// <summary>One chapter as the pipeline records it in <c>config.json</c>.</summary>
public sealed class BookConfigChapterModel
{
    [JsonPropertyName("chapter_number")]
    [JsonConverter(typeof(StringOrNumberConverter))]
    public string? ChapterNumber { get; set; }

    [JsonPropertyName("topic")]
    public string? Topic { get; set; }

    [JsonPropertyName("category")]
    public string? Category { get; set; }

    [JsonPropertyName("status")]
    public string? Status { get; set; }

    [JsonPropertyName("file_path")]
    public string? FilePath { get; set; }

    [JsonPropertyName("segments")]
    public List<BookConfigSegmentModel> Segments { get; set; } = [];

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}

/// <summary>One segment of a chapter as the pipeline records it in <c>config.json</c>.</summary>
public sealed class BookConfigSegmentModel
{
    [JsonPropertyName("segment_number")]
    [JsonConverter(typeof(StringOrNumberConverter))]
    public string? SegmentNumber { get; set; }

    [JsonPropertyName("segment_title")]
    public string? SegmentTitle { get; set; }

    [JsonPropertyName("file_path")]
    public string? FilePath { get; set; }

    [JsonPropertyName("validated")]
    public bool Validated { get; set; }

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}
