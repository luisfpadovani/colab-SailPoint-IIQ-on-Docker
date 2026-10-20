/* Verify the shipped JDBC driver against the running lab SQL server. */
import java.sql.*;
import java.nio.file.Path;

public class JdbcTlsProbe {
    private static Connection connect(String url, String user, String password) throws SQLException {
        return DriverManager.getConnection(url + ";loginTimeout=5", user, password);
    }
    private static void mustReject(String url, String user, String password) throws Exception {
        try (Connection ignored = connect(url, user, password)) {
            throw new AssertionError("JDBC accepted an untrusted certificate or incorrect hostname");
        } catch (SQLException expected) {
            String message = expected.toString().toLowerCase();
            if (!message.contains("certificate") && !message.contains("pkix") && !message.contains("ssl")) throw expected;
        }
    }
    public static void main(String[] args) throws Exception {
        Class.forName("com.microsoft.sqlserver.jdbc.SQLServerDriver");
        String root = "jdbc:sqlserver://sqlserver:1433;encrypt=true;trustServerCertificate=false";
        String[] users = {"identityiq", "identityiqPlugin", "identityiqah", "appMock"};
        String[] keys = {"TEST_IIQ_DB_PASSWORD", "TEST_IIQ_PLUGIN_PASSWORD", "TEST_IIQ_AH_PASSWORD", "TEST_APP_MOCK_PASSWORD"};
        for (int i=0; i<users.length; i++) {
            String url = root + ";databaseName=" + users[i];
            String password = System.getenv(keys[i]);
            if (password == null || password.isEmpty()) throw new IllegalArgumentException("Missing local test credential");
            try (Connection connection = connect(url, users[i], password);
                 Statement statement = connection.createStatement();
                 ResultSet rows = statement.executeQuery("SELECT 1")) {
                if (!rows.next() || rows.getInt(1) != 1) throw new AssertionError("JDBC query failed");
            }
            if (i==0) {
                mustReject(url + ";hostNameInCertificate=wrong.invalid", users[i], password);
                String stockTrust = Path.of(System.getProperty("java.home"), "lib", "security", "cacerts").toString();
                mustReject(url + ";trustStore=" + stockTrust + ";trustStorePassword=changeit", users[i], password);
            }
        }
        System.out.println("PASS: authenticated JDBC TLS for all four logins; unknown issuer and hostname mismatch rejected");
    }
}
