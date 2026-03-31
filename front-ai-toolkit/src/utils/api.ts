const url = import.meta.env.VITE_URL;

interface FetchProps {
  path: string;
  method: string;
  body?: object;
}

const Fetch = async <T = unknown>({ path, method, body }: FetchProps): Promise<T> => {
  const Body = body !== undefined ? JSON.stringify(body) : undefined;

  const fetchOptions: RequestInit = {
    method: method,
    headers: {
      "Content-Type": "application/json",
    },
    ...(Body && { body: Body }),
  };

  try {
    const response = await fetch(url + path, fetchOptions);

    // Verificar el content-type

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Response not OK:", errorText);
      throw new Error(
        `HTTP ${response.status}: ${errorText.substring(0, 100)}`,
      );
    }

    const data = await response.json();
    return data as T;
  } catch (error) {
    console.error("Error en Fetch:", error);
    throw error;
  }
};

export default Fetch;
