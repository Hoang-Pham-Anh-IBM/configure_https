/**
 * ExtractTruststore.java — Extract a server's TLS certificate and import it
 * into a local PKCS12 truststore via keytool.
 *
 * Steps:
 *   1. Extract the certificate from SERVER:PORT with {@code keytool -printcert -sslserver}.
 *   2. Import the certificate into the truststore with {@code keytool -import}.
 *   3. List the truststore contents to verify.
 *
 * Usage:
 *     java ExtractTruststore <server:port>
 *
 * Example:
 *     java ExtractTruststore exxwin22sum25:5543
 */

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

public class ExtractTruststore {

    private static final String STOREPASS = "changeIt";
    private static final Path   JAVA_HOME = Paths.get("C:\\SoftwareAG\\jvm\\jvm");
    private static final Path   KEYTOOL   = JAVA_HOME.resolve("bin").resolve("keytool");

    public static void main(String[] args) throws IOException, InterruptedException {
        if (args.length != 1 || !args[0].contains(":")) {
            System.err.println("Usage: java ExtractTruststore <server:port>");
            System.err.println("Example: java ExtractTruststore exxwin22sum25:5543");
            System.exit(1);
        }

        int colonIdx = args[0].lastIndexOf(':');
        String server = args[0].substring(0, colonIdx);
        String portStr = args[0].substring(colonIdx + 1);

        if (!portStr.matches("\\d+")) {
            System.err.println("ERROR: server:port must be in the form HOST:PORT, e.g. exxwin22sum25:5543 (got \"" + args[0] + "\")");
            System.exit(1);
        }

        String alias      = server;
        Path   certFile   = Paths.get("certificates", alias + ".crt");
        Path   truststore = Paths.get("certificates", alias + ".p12");

        // ── Step 1: Extract certificate ──────────────────────────────────────
        System.out.println();
        System.out.println("=== Step 1: Extract certificate from " + server + ":" + portStr + " ===");

        Files.createDirectories(certFile.getParent());

        int rc = run(
            List.of(KEYTOOL.toString(), "-printcert", "-sslserver", server + ":" + portStr, "-rfc"),
            certFile
        );
        if (rc != 0) {
            System.err.println("ERROR: Failed to extract certificate from " + server + ":" + portStr);
            System.exit(1);
        }
        System.out.println("Certificate saved to " + certFile);

        // ── Step 2: Import certificate into truststore ───────────────────────
        System.out.println();
        System.out.println("=== Step 2: Import certificate into truststore ===");

        rc = run(List.of(
            KEYTOOL.toString(), "-import",
            "-alias",     alias,
            "-file",      certFile.toString(),
            "-keystore",  truststore.toString(),
            "-storetype", "PKCS12",
            "-storepass", STOREPASS,
            "-noprompt"
        ), null);
        if (rc != 0) {
            System.err.println("ERROR: Failed to import certificate into truststore");
            System.exit(1);
        }
        System.out.println("Certificate imported into " + truststore);

        // ── Step 3: Verify truststore contents ───────────────────────────────
        System.out.println();
        System.out.println("=== Step 3: Verify truststore contents ===");

        run(List.of(
            KEYTOOL.toString(), "-list",
            "-keystore",  truststore.toString(),
            "-storetype", "PKCS12",
            "-storepass", STOREPASS
        ), null);

        System.out.println();
        System.out.println("Done.");
    }

    /**
     * Runs a command, optionally redirecting stdout to {@code outFile}.
     *
     * @param cmd     command + arguments
     * @param outFile if non-null, stdout is redirected to this file; otherwise inherited
     * @return process exit code
     */
    private static int run(List<String> cmd, Path outFile) throws IOException, InterruptedException {
        ProcessBuilder pb = new ProcessBuilder(cmd)
            .redirectErrorStream(false)
            .inheritIO();

        if (outFile != null) {
            pb.redirectOutput(outFile.toFile());
        }

        return pb.start().waitFor();
    }
}
