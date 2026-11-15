using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PipelineParser.Models;

[JsonConverter(typeof(FurtherReferenceConverter))]
public sealed class FurtherReferenceModel
{
    [JsonPropertyName("no")]
    public string? No { get; set; }

    [JsonPropertyName("reference")]
    public string? Reference { get; set; }

    [JsonPropertyName("weblink")]
    public string? WebLink { get; set; }

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}
