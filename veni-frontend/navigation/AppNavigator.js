import React from 'react';
import { createSwitchNavigator, createStackNavigator } from 'react-navigation';

import MainTabNavigator from './MainTabNavigator';
import LoginScreen from "../screens/LoginScreen";
import SettingsScreen from "../screens/SettingsScreen";
import FriendsListScreen from "../screens/FriendsListScreen";
import AmIFreeScreen from "../screens/AmIFreeScreen";

const defaultTabNavigationOptions = {
    header: <MainTabNavigator />
}
const LoginStack = createStackNavigator({Login: LoginScreen});
const AppStack = createStackNavigator({
        AmIFree: { screen: AmIFreeScreen }, //navigationOptions: defaultTabNavigationOptions },
        FriendsList: { screen: FriendsListScreen },
        Settings: { screen: SettingsScreen }
})

export default createSwitchNavigator(
    {
        // You could add another route here for authentication.
        // Read more at https://reactnavigation.org/docs/en/auth-flow.html
        Login: LoginStack,
        App: AppStack,
    },
    {
        initialRouteName: 'Login'
    }

);
