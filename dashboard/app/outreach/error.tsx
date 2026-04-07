"use client";

import { useEffect } from "react";

export default function PageError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center space-y-4 p-8 text-center">
      <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-8 max-w-md w-full space-y-4">
        <h2 className="text-lg font-semibold text-destructive">
          Error al cargar esta sección
        </h2>
        <p className="text-sm text-muted-foreground">
          {error.message || "Se produjo un error inesperado."}
        </p>
        <button
          onClick={reset}
          className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
        >
          Reintentar
        </button>
      </div>
    </div>
  );
}
