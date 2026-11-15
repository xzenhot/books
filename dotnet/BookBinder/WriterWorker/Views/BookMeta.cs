using System;
using System.Globalization;
using System.IO;

namespace WriterWorker.Views
{
    /// <summary>
    /// Formats the "created by" / "created on" metadata shown in the header of every book page.
    /// </summary>
    public static class BookMeta
    {
        public const string Unknown = "unknown";

        /// <summary>User name to show when a file does not record one.</summary>
        public static string CurrentUser
        {
            get
            {
                var user = Environment.UserName;
                return string.IsNullOrWhiteSpace(user) ? Unknown : user;
            }
        }

        public static string Text(string? value)
            => string.IsNullOrWhiteSpace(value) ? Unknown : value.Trim();

        /// <summary>
        /// Normalises the timestamps found in writer workspaces: ISO values
        /// (<c>2026-11-12T05:46:14+00:00</c>), date only (<c>2026-11-10</c>) and free text such as
        /// <c>10-11-2026 12:36:10</c>. Unparsable values are returned unchanged.
        /// </summary>
        public static string Date(string? value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return Unknown;
            }

            var text = value.Trim();
            if (DateTimeOffset.TryParse(text, CultureInfo.InvariantCulture, DateTimeStyles.AssumeLocal, out var when)
                || DateTimeOffset.TryParse(text, CultureInfo.CurrentCulture, DateTimeStyles.AssumeLocal, out when))
            {
                return when.TimeOfDay == TimeSpan.Zero
                    ? when.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture)
                    : when.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture);
            }

            return text;
        }

        /// <summary>Date from metadata, falling back to the folder creation time and then to <see cref="Unknown"/>.</summary>
        public static string Date(string? value, string? directory)
            => string.IsNullOrWhiteSpace(value) ? FolderCreatedOn(directory) : Date(value);

        /// <summary>Creation time of a folder, used when no metadata file records a date.</summary>
        public static string FolderCreatedOn(string? directory)
        {
            try
            {
                if (!string.IsNullOrWhiteSpace(directory) && Directory.Exists(directory))
                {
                    return Directory.GetCreationTime(directory).ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture);
                }
            }
            catch (Exception exception) when (exception is IOException
                or UnauthorizedAccessException
                or ArgumentException
                or NotSupportedException)
            {
            }

            return Unknown;
        }
    }
}
