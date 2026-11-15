using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PipelineParser.Models;

public sealed class ChapterModel
{
    [JsonPropertyName("chapter_index")]
    public int ChapterIndex { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("word_target")]
    public int WordTarget { get; set; }

    /// <summary>Set for poetry chapters; novels omit it.</summary>
    [JsonPropertyName("segment_count")]
    public int? SegmentCount { get; set; }

    [JsonPropertyName("chapter_title")]
    public string? ChapterTitle { get; set; }

    [JsonPropertyName("chapter_summary")]
    public string? ChapterSummary { get; set; }

    [JsonPropertyName("further_references")]
    public List<FurtherReferenceModel> FurtherReferences { get; set; } = [];

    [JsonPropertyName("segments")]
    public List<SegmentModel> Segments { get; set; } = [];

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}
