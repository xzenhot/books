using System;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace WriterWorker.Parser.PipelineParser.Models;

/// <summary>
/// Reads a further reference written either as an object
/// (<c>{"no": "1", "reference": "...", "weblink": "..."}</c>) or as a bare string
/// (<c>"1"</c>), which older workspaces contain. A bare string keeps its position as the number
/// and becomes the reference text, so a plan that uses the short form still loads.
/// </summary>
internal sealed class FurtherReferenceConverter : JsonConverter<FurtherReferenceModel>
{
    public override FurtherReferenceModel Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        if (reader.TokenType == JsonTokenType.String)
        {
            var text = reader.GetString();
            return new FurtherReferenceModel { Reference = text };
        }

        if (reader.TokenType != JsonTokenType.StartObject)
        {
            throw new JsonException("A further reference must be an object or a string.");
        }

        string? no = null;
        string? reference = null;
        string? webLink = null;
        System.Collections.Generic.Dictionary<string, JsonElement>? extra = null;

        while (reader.Read() && reader.TokenType != JsonTokenType.EndObject)
        {
            if (reader.TokenType != JsonTokenType.PropertyName)
            {
                throw new JsonException("A further reference must hold properties.");
            }

            var name = reader.GetString();
            reader.Read();

            switch (name?.ToLowerInvariant())
            {
                case "no":
                case "number":
                    no = ReadText(ref reader);
                    break;
                case "reference":
                case "text":
                    reference = ReadText(ref reader);
                    break;
                case "weblink":
                case "link":
                    webLink = ReadText(ref reader);
                    break;
                default:
                    (extra ??= new(StringComparer.Ordinal))[name ?? string.Empty] = JsonElement.ParseValue(ref reader);
                    break;
            }
        }

        return new FurtherReferenceModel
        {
            No = no,
            Reference = reference,
            WebLink = webLink,
            AdditionalProperties = extra,
        };
    }

    public override void Write(Utf8JsonWriter writer, FurtherReferenceModel value, JsonSerializerOptions options)
    {
        writer.WriteStartObject();
        if (value.No is not null)
        {
            writer.WriteString("no", value.No);
        }

        if (value.Reference is not null)
        {
            writer.WriteString("reference", value.Reference);
        }

        if (value.WebLink is not null)
        {
            writer.WriteString("weblink", value.WebLink);
        }

        if (value.AdditionalProperties is { Count: > 0 })
        {
            foreach (var property in value.AdditionalProperties)
            {
                writer.WritePropertyName(property.Key);
                property.Value.WriteTo(writer);
            }
        }

        writer.WriteEndObject();
    }

    private static string? ReadText(ref Utf8JsonReader reader) => reader.TokenType switch
    {
        JsonTokenType.String => reader.GetString(),
        JsonTokenType.Number => reader.TryGetInt64(out var number)
            ? number.ToString(System.Globalization.CultureInfo.InvariantCulture)
            : reader.GetDouble().ToString(System.Globalization.CultureInfo.InvariantCulture),
        JsonTokenType.Null => null,
        _ => JsonElement.ParseValue(ref reader).ToString(),
    };
}
