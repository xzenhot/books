using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PipelineParser.Models;

/// <summary>
/// Tracks chapter completion for a book in <c>progress.json</c>.
/// </summary>
public sealed class ProgressModel
{
    [JsonPropertyName("title")]
    public string? Title { get; set; }

    [JsonPropertyName("book_name")]
    public string? BookName { get; set; }

    [JsonPropertyName("language")]
    public string? Language { get; set; }

    [JsonPropertyName("form")]
    public string? Form { get; set; }

    [JsonPropertyName("factory")]
    public string? Factory { get; set; }

    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("provider")]
    public string? Provider { get; set; }

    [JsonPropertyName("context")]
    public string? Context { get; set; }

    [JsonPropertyName("source_terms")]
    public List<string> SourceTerms { get; set; } = [];

    [JsonPropertyName("total_chapters")]
    public int TotalChapters { get; set; }

    [JsonPropertyName("completed_chapters")]
    public int CompletedChapters { get; set; }

    [JsonPropertyName("written_chapters")]
    public int? WrittenChapters { get; set; }

    [JsonPropertyName("current_chapter")]
    [JsonConverter(typeof(StringOrNumberConverter))]
    public string? CurrentChapter { get; set; }

    [JsonPropertyName("chapters")]
    public List<ProgressChapterModel> Chapters { get; set; } = [];

    [JsonPropertyName("published")]
    public bool? Published { get; set; }

    [JsonPropertyName("published_at")]
    public string? PublishedAt { get; set; }

    [JsonPropertyName("published_version")]
    public int? PublishedVersion { get; set; }

    [JsonPropertyName("updated_by")]
    public string? UpdatedBy { get; set; }

    [JsonPropertyName("updated_date")]
    public string? UpdatedDate { get; set; }

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}
