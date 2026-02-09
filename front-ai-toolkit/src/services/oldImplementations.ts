// --- Function to ingest without stream ---

// const handleIngest = async () => {
//   try {
//     setLoading(true);

//     new URL(url);

//     const body: Ingestrequest = {
//       url: url,
//       domain: typeof domain === "string" ? domain : undefined,
//       topic: typeof topic === "string" ? topic : undefined,
//     };

//     await ingestURLFetch(body);

//     CustomizedToast({ type: "info", msg: "Document consumed successfully" });
//   } catch (err) {
//     const msg = err instanceof Error ? err.message : "Unknown error";
//     CustomizedToast({ type: "error", msg: msg });
//   } finally {
//     setLoading(false);
//     setUrl("");
//   }
// };

// --- Function to ingest with stream

// const handleIngestStream = async () => {
//   try {
//     setLoading(true);

//     new URL(url);

//     const body: Ingestrequest = {
//       url: url,
//       domain: typeof domain === "string" ? domain : undefined,
//       topic: typeof topic === "string" ? topic : undefined,
//     };

//     try {
//       const response = await ingestURLStream(body);

//       const reader = response.body!.getReader();
//       const decoder = new TextDecoder();

//       while (true) {
//         const { done, value } = await reader.read();

//         if (done) {
//           break;
//         }

//         const chunk = decoder.decode(value);
//         const lines = chunk.split("\n\n").filter((line) => line.trim());

//         for (const line of lines) {
//           if (line.startsWith("data: ")) {
//             const data = JSON.parse(line.slice(6));

//             if (data.error) {
//               CustomizedToast({ type: "error", msg: data.error });
//               break;
//             }

//             setProgress(data.progress);
//             setStatusMessage(data.step);

//             if (data.progress === 100) {
//               CustomizedToast({
//                 type: "success",
//                 msg: `Processed ${data.chunks_processed} chunks`,
//               });
//               break;
//             }
//           }
//         }
//       }
//     } catch (error) {
//       CustomizedToast({ type: "error", msg: String(error) });
//     }
//   } finally {
//     setLoading(false);
//     setUrl("");
//   }
// };

// const handleIngestPDFStream = async () => {
//   if (!file) {
//     CustomizedToast({
//       type: "error",
//       msg: "Por favor selecciona un archivo PDF",
//     });
//     return;
//   }

//   try {
//     setLoading(true);
//     setProgress(0);

//     // Create FormData container
//     const formData = new FormData();

//     // Add the fields
//     formData.append("file", file);
//     formData.append("source", file.name);
//     formData.append("domain", domain || "general");
//     formData.append("topic", topic || "pdf-upload");

//     try {
//       // Fetch
//       const response = await ingestFile(formData);

//       if (!response.ok) throw new Error("Error en la subida");

//       // Stream logic
//       const reader = response.body!.getReader();
//       const decoder = new TextDecoder();

//       while (true) {
//         const { done, value } = await reader.read();

//         if (done) {
//           break;
//         }

//         const chunk = decoder.decode(value);
//         const lines = chunk.split("\n\n").filter((line) => line.trim());

//         for (const line of lines) {
//           if (line.startsWith("data: ")) {
//             const data = JSON.parse(line.slice(6));

//             if (data.error) {
//               CustomizedToast({ type: "error", msg: data.error });
//               break;
//             }

//             setProgress(data.progress);
//             setStatusMessage(data.step);

//             if (data.progress === 100) {
//               CustomizedToast({
//                 type: "success",
//                 msg: `Processed ${data.chunks_processed} chunks`,
//               });
//               break;
//             }
//           }
//         }
//       }
//     } catch (error) {
//       CustomizedToast({ type: "error", msg: String(error) });
//     }
//   } finally {
//     setLoading(false);
//   }
// };
