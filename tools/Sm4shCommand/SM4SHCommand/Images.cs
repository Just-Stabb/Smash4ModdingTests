using System.Drawing;
using System.IO;
using System.Reflection;

namespace Sm4shCommand
{
    /// <summary>
    /// The program's images, embedded as plain PNG/ICO files (Resources\*.png, Resources\app.ico) and
    /// loaded directly, so they don't depend on how a build tool serializes images into .resources
    /// (an image that didn't deserialize stopped the program before its window appeared).
    /// </summary>
    static class Images
    {
        static Stream Open(string name)
        {
            return Assembly.GetExecutingAssembly().GetManifestResourceStream("Sm4shCommand.Images." + name);
        }

        /// <summary>
        /// The image, or null if it's missing or unreadable (the button just has no picture then).
        /// </summary>
        public static Image Load(string name)
        {
            try
            {
                using (var s = Open(name))
                {
                    if (s == null)
                        return null;
                    using (var img = Image.FromStream(s))
                        return new Bitmap(img); // a copy that doesn't need the stream to stay open
                }
            }
            catch
            {
                return null;
            }
        }

        public static Icon LoadIcon(string name)
        {
            try
            {
                using (var s = Open(name))
                    return s == null ? null : new Icon(s);
            }
            catch
            {
                return null;
            }
        }
    }
}
