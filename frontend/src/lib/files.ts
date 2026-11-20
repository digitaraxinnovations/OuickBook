/** Opens a downloaded file (e.g. a PDF) in a new browser tab. */
export function openBlobInNewTab(blob: Blob): void {
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank");
  // Give the new tab time to load the file before freeing it.
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

/** Reads a file chosen by the user as base64 text (without the "data:...;base64," prefix). */
export function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result);
      resolve(text.substring(text.indexOf(",") + 1));
    };
    reader.onerror = () => reject(new Error("Could not read the file."));
    reader.readAsDataURL(file);
  });
}

/** Saves a downloaded file (e.g. a CSV export) to the user's computer. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
