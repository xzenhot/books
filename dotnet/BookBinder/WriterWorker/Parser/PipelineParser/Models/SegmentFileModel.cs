using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PipelineParser.Models;

/// <summary>
/// Per-segment state file at <c>chapters/{n}/segments/{i}/segment.json</c>.
/// </summary>
internal sealed class SegmentFileModel
{
    [JsonPropertyName("level")]
    public string? Level { get; set; }

    [JsonPropertyName("state")]
    public string? State { get; set; }

    [JsonPropertyName("chapter_index")]
    public int? ChapterIndex { get; set; }

    [JsonPropertyName("segment_index")]
    public int? SegmentIndex { get; set; }

    [JsonPropertyName("total_segments")]
    public int? TotalSegments { get; set; }

    [JsonPropertyName("segment_title")]
    public string? SegmentTitle { get; set; }

    [JsonPropertyName("segment_summary")]
    public string? SegmentSummary { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("word_target")]
    public int? WordTarget { get; set; }

    [JsonPropertyName("further_references")]
    public List<FurtherReferenceModel> FurtherReferences { get; set; } = [];

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? AdditionalProperties { get; set; }
}

/// <summary>
/// Reads a chapter's <c>segments</c> array whether it holds full segment objects, bare
/// numbers (<c>[1]</c>) or segment names (<c>["Introduction"]</c>).
/// </summary>
internal sealed class SegmentFileListConverter : JsonConverter<List<SegmentFileModel>>
{
    public override List<SegmentFileModel> Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        if (reader.TokenType != JsonTokenType.StartArray)
        {
            throw new JsonException($"Expected an array of segments but found {reader.TokenType}.");
        }

        var segments = new List<SegmentFileModel>();
        while (reader.Read() && reader.TokenType != JsonTokenType.EndArray)
        {
            segments.Add(ReadSegment(ref reader, options));
        }

        return segments;
    }

    public override void Write(Utf8JsonWriter writer, List<SegmentFileModel> value, JsonSerializerOptions options)
    {
        writer.WriteStartArray();
        foreach (var segment in value)
        {
            JsonSerializer.Serialize(writer, segment, options);
        }

        writer.WriteEndArray();
    }

    private static SegmentFileModel ReadSegment(ref Utf8JsonReader reader, JsonSerializerOptions options)
    {
        switch (reader.TokenType)
        {
            case JsonTokenType.Number:
                return new SegmentFileModel
                {
                    SegmentIndex = reader.TryGetInt32(out var index) ? index : null,
                };

            case JsonTokenType.String:
                var name = reader.GetString();
                return new SegmentFileModel
                {
                    Name = name,
                    SegmentIndex = int.TryParse(name, NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed)
                        ? parsed
                        : null,
                };

            case JsonTokenType.StartObject:
                return JsonSerializer.Deserialize<SegmentFileModel>(ref reader, options) ?? new SegmentFileModel();

            default:
                throw new JsonException($"Unexpected segment token {reader.TokenType}.");
        }
    }
}
