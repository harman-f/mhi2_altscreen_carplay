/* SPDX-License-Identifier: MIT
 * Small request-token state machine for one owned icon widget.
 */
package de.mibr.hmi;

final class MibrIconLoadState {
    private String path;
    private long generation;
    private boolean requested;
    private boolean loaded;
    private boolean failed;
    private boolean disposed;

    boolean selectPath(String nextPath) {
        if (nextPath == null || nextPath.length() == 0) return false;
        if (nextPath.equals(path) && !disposed) return false;
        path = nextPath;
        generation++;
        requested = false;
        loaded = false;
        failed = false;
        disposed = false;
        return true;
    }

    String path() {
        return path;
    }

    boolean needsRequest() {
        return !disposed && !requested && !loaded && !failed && path != null;
    }

    long beginRequest() {
        if (!needsRequest()) return -1L;
        requested = true;
        return generation;
    }

    boolean isCurrent(long token, String requestPath) {
        return !disposed && token == generation && path != null && path.equals(requestPath);
    }

    boolean markLoaded(long token, String requestPath) {
        if (!isCurrent(token, requestPath) || !requested) return false;
        requested = false;
        loaded = true;
        failed = false;
        return true;
    }

    boolean markFailed(long token, String requestPath) {
        if (!isCurrent(token, requestPath) || !requested) return false;
        requested = false;
        loaded = false;
        failed = true;
        return true;
    }

    boolean isLoaded() {
        return loaded && !disposed;
    }

    boolean isFailed() {
        return failed;
    }

    void markRenderFailed() {
        if (!disposed) {
            loaded = false;
            requested = false;
            failed = true;
        }
    }

    void dispose() {
        disposed = true;
        generation++;
        requested = false;
        loaded = false;
        failed = false;
        path = null;
    }
}