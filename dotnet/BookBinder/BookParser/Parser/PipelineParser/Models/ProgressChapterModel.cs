using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PipelineParser.Models;

public sealed class ProgressChapterModel
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

    [JsonPropertyName("completed_date")]
    public string? CompletedDate { get; set; }

    [JsonPropertyName("written")]
    public bool? Written { get; set; }

    [JsonPropertyName("validated")]
    public bool? Validated { get; set; }

    [JsonPropertyName("published")]
    public bool? Published { get; set; }

    [JsonPropertyName("published_version")]
    public int? PublishedVersion { get; set; }

    [JsonPropertyName("published_sha256")]
    public string? PublishedSha256 { get; set; }

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}
