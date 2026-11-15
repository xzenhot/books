using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PipelineParser.Models;

internal sealed class SegmentModel
{
    [JsonPropertyName("segment_index")]
    public int SegmentIndex { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("word_target")]
    public int WordTarget { get; set; }

    [JsonPropertyName("segment_title")]
    public string? SegmentTitle { get; set; }

    [JsonPropertyName("segment_summary")]
    public string? SegmentSummary { get; set; }

    [JsonPropertyName("further_references")]
    public List<FurtherReferenceModel> FurtherReferences { get; set; } = [];

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}
