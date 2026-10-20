/* Evaluate the shipped BeanShell rules and verify DN component boundaries. */
import bsh.Interpreter;
import javax.naming.ldap.LdapName;
import javax.xml.parsers.DocumentBuilderFactory;
import sailpoint.object.Identity;

public class LdapDnProbe {
    public static class Field {
        private final String value, label;
        Field(String value, String label) { this.value = value; this.label = label; }
        public String getValue() { return value; }
        public String getDisplayableName() { return label; }
    }
    public static class Form {
        private final Field field;
        Form(String value, String label) { field = new Field(value, label); }
        public Field getField(String name) { return field; }
    }
    private static String rule(String name) throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        return factory.newDocumentBuilder().parse(
            "/usr/local/tomcat/webapps/identityiq/WEB-INF/config/custom/Rule/Rule-OpenldapSet" + name + "Dn.xml")
            .getElementsByTagName("Source").item(0).getTextContent();
    }
    private static void verify(Object result, String cn, String ou) throws Exception {
        LdapName dn = new LdapName((String) result);
        if (dn.size() != 3 || !"corp1".equals(dn.getRdn(0).getValue())
            || !ou.equals(dn.getRdn(1).getValue()) || !"cn".equalsIgnoreCase(dn.getRdn(2).getType())
            || !cn.equals(dn.getRdn(2).getValue()))
            throw new AssertionError("DN escaped component boundaries were not preserved");
    }
    public static void main(String[] args) throws Exception {
        String account = rule("Account"), group = rule("Group");
        String[] names = {"00000001", "Doe, Jane", "Admin+Root", "#hash", " leading ",
            "x,ou=Admins,dc=evil", "a=b", "back\\slash", "quote\"name", "semi;colon", "nul\u0000name"};
        for (String name : names) {
            Interpreter interpreter = new Interpreter();
            Identity identity = new Identity();
            identity.setName(name);
            interpreter.set("identity", identity);
            // Identity normalizes its name; the rule must preserve the value it receives.
            verify(interpreter.eval(account), identity.getName(), "Users");
            interpreter.set("form", new Form(name, "unused"));
            verify(interpreter.eval(group), name, "Groups");
            interpreter.set("form", new Form(null, name));
            verify(interpreter.eval(group), name, "Groups");
        }
        System.out.println("PASS: shipped LDAP DN rules preserve CN values and subtree boundaries, including group fallback");
    }
}
