/**
 * Saves the login token in the browser.
 * Kept in its own class so the storage method can change in one place.
 */
export class TokenStorage {
  private key: string;

  constructor(key: string) {
    this.key = key;
  }

  get(): string | null {
    if (typeof window === "undefined") {
      return null;
    }
    return window.localStorage.getItem(this.key);
  }

  save(token: string): void {
    window.localStorage.setItem(this.key, token);
  }

  clear(): void {
    window.localStorage.removeItem(this.key);
  }
}
