import { Link } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

export default function ModalScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Alice Mobile</Text>
      <Text style={styles.body}>
        Point the app at your local `hub-api` instance. On a phone, use your LAN IP instead of
        `127.0.0.1`.
      </Text>
      <Link href="/" dismissTo style={styles.link}>
        <Text style={styles.linkText}>Back to overview</Text>
      </Link>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f2ede6',
    gap: 16,
    justifyContent: 'center',
    padding: 24,
  },
  title: {
    color: '#172026',
    fontSize: 28,
    fontWeight: '700',
  },
  body: {
    color: '#5c6770',
    fontSize: 16,
    lineHeight: 24,
  },
  link: {
    paddingVertical: 8,
  },
  linkText: {
    color: '#27434a',
    fontSize: 16,
    fontWeight: '700',
  },
});
