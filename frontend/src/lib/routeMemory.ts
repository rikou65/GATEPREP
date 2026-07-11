const AUTH_RETURN_TO_KEY = "authReturnTo";
const LAST_PROTECTED_PATH_KEY = "lastProtectedPath";

const AUTH_ROUTES = new Set(["/", "/auth/callback"]);

export function currentPath() {
  return `${window.location.pathname}${window.location.search}`;
}

export function rememberProtectedPath(path = currentPath()) {
  const pathname = path.split("?")[0];
  if (AUTH_ROUTES.has(pathname)) return;
  sessionStorage.setItem(LAST_PROTECTED_PATH_KEY, path);
}

export function setAuthReturnTo(path: string) {
  sessionStorage.setItem(AUTH_RETURN_TO_KEY, path);
}

export function getAuthReturnTo(fallback = "/dashboard") {
  return (
    sessionStorage.getItem(AUTH_RETURN_TO_KEY) ||
    sessionStorage.getItem(LAST_PROTECTED_PATH_KEY) ||
    fallback
  );
}

export function consumeAuthReturnTo(fallback = "/dashboard") {
  const path = getAuthReturnTo(fallback);
  sessionStorage.removeItem(AUTH_RETURN_TO_KEY);
  return path;
}
