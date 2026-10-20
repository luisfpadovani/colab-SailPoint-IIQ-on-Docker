/* Regression probe for the licensed IIQ connector. Contains no product implementation. */
import java.lang.reflect.*;
import java.sql.*;
import java.util.*;
import javax.xml.parsers.*;
import javax.xml.xpath.*;
import org.w3c.dom.Document;
import sailpoint.connector.JDBCConnector;
import sailpoint.object.Application;
import sailpoint.object.Attributes;
import sailpoint.object.Schema;

public class JdbcBindingProbe {
    static Object defaultValue(Class<?> type) {
        if (!type.isPrimitive() || type == void.class) return null;
        if (type == boolean.class) return false;
        if (type == int.class) return 0;
        if (type == long.class) return 0L;
        return null;
    }
    public static void main(String[] args) throws Exception {
        Application application = new Application();
        application.setName("JDBC binding regression");
        Attributes<String,Object> attributes = new Attributes<>();
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        Document source = factory.newDocumentBuilder().parse("/usr/local/tomcat/webapps/identityiq/WEB-INF/config/custom/Application/Application-Jdbc.xml");
        XPath xpath = XPathFactory.newInstance().newXPath();
        for (String key : new String[]{"getObjectSQL", "group.getObjectSQL"})
            attributes.put(key, xpath.evaluate("//entry[@key='" + key + "']/@value", source));
        application.setAttributes(attributes);
        String[] payloads = {"00000001", "Administrator", "' OR 1=1 --", "x'; SELECT 1; --", "O'Connor", "?$(identity)"};
        Method fetch = JDBCConnector.class.getDeclaredMethod("getFetchSQL", Schema.class, String.class, boolean.class);
        fetch.setAccessible(true);
        Field identity = JDBCConnector.class.getDeclaredField("identityAttribute");
        identity.setAccessible(true);
        Method execute = JDBCConnector.class.getDeclaredMethod("execute", PreparedStatement.class,
            CallableStatement.class, Connection.class, String.class, Boolean.class, Boolean.class);
        execute.setAccessible(true);
        for (String objectType : new String[]{"account", "group"}) {
            Schema schema = new Schema();
            schema.setObjectType(objectType);
            schema.setIdentityAttribute(objectType.equals("account") ? "login" : "name");
            application.addSchema(schema);
            for (String payload : payloads) {
                JDBCConnector connector = new JDBCConnector(application);
                String sql = (String) fetch.invoke(connector, schema, payload, false);
                String expected = "exec " + (objectType.equals("account") ? "GET_BY_USER" : "GET_BY_GROUP") + " ?";
                if (!expected.equals(sql)) throw new AssertionError("Query is not parameterized for " + objectType);
                identity.set(connector, payload);
                Map<Integer,String> bindings = new HashMap<>();
                ResultSet rs = (ResultSet) Proxy.newProxyInstance(JdbcBindingProbe.class.getClassLoader(), new Class[]{ResultSet.class},
                    (proxy, method, parameters) -> defaultValue(method.getReturnType()));
                PreparedStatement statement = (PreparedStatement) Proxy.newProxyInstance(JdbcBindingProbe.class.getClassLoader(), new Class[]{PreparedStatement.class},
                    (proxy, method, parameters) -> {
                        if (method.getName().equals("setString")) bindings.put((Integer)parameters[0], (String)parameters[1]);
                        if (method.getName().equals("execute")) return true;
                        if (method.getName().equals("getResultSet") || method.getName().equals("executeQuery")) return rs;
                        if (method.getName().equals("getUpdateCount")) return -1;
                        return defaultValue(method.getReturnType());
                    });
                Connection connection = (Connection) Proxy.newProxyInstance(JdbcBindingProbe.class.getClassLoader(), new Class[]{Connection.class},
                    (proxy, method, parameters) -> {
                        if (method.getName().equals("prepareStatement")) {
                            if (!expected.equals(parameters[0])) throw new AssertionError("Unsafe SQL sent to JDBC");
                            return statement;
                        }
                        return defaultValue(method.getReturnType());
                    });
                execute.invoke(connector, null, null, connection, sql, false, false);
                if (!payload.equals(bindings.get(1)) || bindings.size() != 1) throw new AssertionError("Identity was not bound as data");
            }
        }
        System.out.println("PASS: IIQ JDBC account/group queries bind all identities and injection payloads with setString");
    }
}
