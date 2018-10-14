import React from 'react';
import { Platform, StatusBar, StyleSheet, View } from 'react-native';
import { AppLoading, Asset, Font, Icon } from 'expo';
import LoginScreen from "./screens/LoginScreen";
import {createStackNavigator} from "react-navigation";
import { StackNavigator } from 'react-navigation';
import FriendsListScreen from "./screens/FriendsListScreen";
import AmIFreeScreen from "./screens/AmIFreeScreen";
import AppNavigator from "./navigation/AppNavigator";
import SettingsScreen from "./screens/SettingsScreen";

const AppStackNavigator = createStackNavigator(
    {
        AmIFree: {
          screen: AmIFreeScreen,
          navigationOptions: { headerLeft: null }
        },
        FriendsList: { screen: FriendsListScreen },
        Login: { screen: LoginScreen },
        Settings: { screen: SettingsScreen }
    },
    {
      initialRouteName: 'Login'
    }
);

export default class App extends React.Component {
  state = {
    isLoadingComplete: false,
      firstLaunch: true
  };

  render() {
  // return <AppStackNavigator />;
    if (!this.state.isLoadingComplete && !this.props.skipLoadingScreen) {
      return (
        <AppLoading
          startAsync={this._loadResourcesAsync}
          onError={this._handleLoadingError}
          onFinish={this._handleFinishLoading}
        />
      );
    // } else if (this.state.firstLaunch) {
    //   this.setState({firstLaunch: false})
    //   return (
          {/*<LoginScreen />*/}
      // )
    } else {
      return (
        <View style={styles.container}>
          {Platform.OS === 'ios' && <StatusBar barStyle="default" />}
          <AppNavigator />
        </View>
      );
    }
  }

  _loadResourcesAsync = async () => {
    return Promise.all([
      Asset.loadAsync([
        require('./assets/images/robot-dev.png'),
        require('./assets/images/robot-prod.png'),
      ]),
      Font.loadAsync({
        // This is the font that we are using for our tab bar
        ...Icon.Ionicons.font,
        // We include SpaceMono because we use it in LoginScreenn.js. Feel free
        // to remove this if you are not using it in your app
        'space-mono': require('./assets/fonts/SpaceMono-Regular.ttf'),
      }),
    ]);
  };

  _handleLoadingError = error => {
    // In this case, you might want to report the error to your error
    // reporting service, for example Sentry
    console.warn(error);
  };

  _handleFinishLoading = () => {
    this.setState({ isLoadingComplete: true });
  };
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
});
