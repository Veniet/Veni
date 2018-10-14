import React from 'react';
import {
    Platform,
    ScrollView,
    StyleSheet,
    Text,
    View,
    Button,
    Alert,
    TextInput, Image
} from 'react-native';
import { WebBrowser } from 'expo';
import { StackActions, NavigationActions } from 'react-navigation';



export default class LoginScreen extends React.Component {

    static navigationOptions = {
    header: null,
  };

  constructor(props) {
      super(props);
      this.state = {
          loginUsername: "Your Phone Number",
          loginPassword: "Your Password"
      }
  }

  clickLogin() {
      //TODO - make the auth call
      const authed = true;
      if (authed) {
          // this.props.navigation.dispatch(this.__resetAction("App"));
          this.props.navigation.navigate("App");

      } else {
          Alert.alert("Incorrect password. Please try again...")
      }
  }

  render() {
    return (
      <View style={styles.container}>
        <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>

          <View style={styles.getStartedContainer}>

            <Text style={styles.getStartedText}>
               New to Veni? Click Register to get started!
            </Text>

            <Button title="Register" onPress={() => {Alert.alert("Go to register page...")}} />
          </View>

          <View style={styles.loginContainer}>
              <Text> Login to get started... </Text>
              <TextInput style={styles.inputBox}
                           value={this.state.loginUsername}
                           onChangeText={(text) => {this.setState({text})}}/>
              <TextInput style={styles.inputBox}
                           value={this.state.loginPassword}
                           onChangeText={(text) => {this.setState({text})}}/>
              <Button title="Login" onPress={this.clickLogin.bind(this)} />

          </View>
          <View styles={styles.animationContainer}>
            <Image style={{flex: 1, width: 100, height: 100, alignSelf: "center"}} source={require("../assets/images/Final.gif")} />
          </View>
        </ScrollView>
      </View>
    );
  }

  onPressRegister() {
      alert('hi');
  }

  _handleLearnMorePress = () => {
    WebBrowser.openBrowserAsync('https://docs.expo.io/versions/latest/guides/development-mode');
  };

  _handleHelpPress = () => {
    WebBrowser.openBrowserAsync(
      'https://docs.expo.io/versions/latest/guides/up-and-running.html#can-t-see-your-changes'
    );
  };
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  developmentModeText: {
    marginBottom: 20,
    color: 'rgba(0,0,0,0.4)',
    fontSize: 14,
    lineHeight: 19,
    textAlign: 'center',
  },
  contentContainer: {
    paddingTop: 30,
  },
  welcomeContainer: {
    alignItems: 'center',
    marginTop: 10,
    marginBottom: 20,
  },
  welcomeImage: {
    width: 100,
    height: 80,
    resizeMode: 'contain',
    marginTop: 3,
    marginLeft: -10,
  },
  getStartedContainer: {
    alignItems: 'center',
    marginHorizontal: 10,
  },
  homeScreenFilename: {
    marginVertical: 7,
  },
  codeHighlightText: {
    color: 'rgba(96,100,109, 0.8)',
  },
  codeHighlightContainer: {
    backgroundColor: 'rgba(0,0,0,0.05)',
    borderRadius: 3,
    paddingHorizontal: 4,
  },
  getStartedText: {
    fontSize: 17,
    color: 'rgba(96,100,109, 1)',
    lineHeight: 24,
    textAlign: 'center',
  },
  tabBarInfoContainer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    ...Platform.select({
      ios: {
        shadowColor: 'black',
        shadowOffset: { height: -3 },
        shadowOpacity: 0.1,
        shadowRadius: 3,
      },
      android: {
        elevation: 20,
      },
    }),
    alignItems: 'center',
    backgroundColor: '#fbfbfb',
    paddingVertical: 20,
  },
  tabBarInfoText: {
    fontSize: 17,
    color: 'rgba(96,100,109, 1)',
    textAlign: 'center',
  },
  navigationFilename: {
    marginTop: 5,
  },
  loginContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      height:500
  },
  helpLink: {
    paddingVertical: 15,
  },
  helpLinkText: {
    fontSize: 14,
    color: '#2e78b7',
  },
    inputBox: {
      width: 200,
      height: 40
    },
    animationContainer: {
        flex: 1,
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100%'

    }
});
