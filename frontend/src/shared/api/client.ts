type QueryValue = string | number | boolean | null | undefined;

function buildQueryString(params: Record<string, QueryValue> | undefined): string {
  if (!params) {
    return "";
  }

  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) {
      continue;
    }
    searchParams.set(key, String(value));
  }

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

export async function apiGet<T>(path: string, params?: Record<string, QueryValue>): Promise<T> {
  const response = await fetch(`${path}${buildQueryString(params)}`);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}
