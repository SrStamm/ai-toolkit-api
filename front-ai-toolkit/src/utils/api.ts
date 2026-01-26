const url = import.meta.env.VITE_URL;

type FetchProps = {
  path: string;
  method: string;
  body?: object;
};

const Fetch = async ({ path, method, body }: FetchProps) => {
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
    const contentType = response.headers.get("content-type");

    // Si no es JSON, leer como texto primero
    if (!contentType || !contentType.includes("application/json")) {
      const text = await response.text();
      console.error(
        "❌ Respuesta no es JSON. Recibido:",
        text.substring(0, 500),
      );

      // Si es un error 404, 500, etc., lanzar error
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${text.substring(0, 100)}`);
      }

      return response;
    }

    if (!response.ok) {
      const errorText = await response.text();
      console.error("❌ Response not OK:", errorText);
      throw new Error(
        `HTTP ${response.status}: ${errorText.substring(0, 100)}`,
      );
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("🔥 Error en Fetch:", error);
    throw error;
  }
};

export default Fetch;
