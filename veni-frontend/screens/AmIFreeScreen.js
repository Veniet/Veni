import React from 'react';
import {Alert, TouchableOpacity, ScrollView, StyleSheet, Text, Image, View, Platform} from 'react-native';
import {createBottomTabNavigator, createStackNavigator, NavigationActions} from 'react-navigation';
import MainTabNavigator from "../navigation/MainTabNavigator";
import FriendsListScreen from "./FriendsListScreen";
import TabBarIcon from "../components/TabBarIcon";
import SettingsScreen from "./SettingsScreen";


/* export default */ class AmIFreeScreen extends React.Component {
    static navigationOptions = {
        title: 'Free tonight? Touch my button...'
    };

    clickAmIFree() {
        Alert.alert("test");
        fetch()
            .then((response) => {
                Alert.alert("success");
            })
            .catch((error) => {
                Alert.alert("error");
            })
    }

    render() {
        return (
                <TouchableOpacity style={styles.container} onPress={() => {this.clickAmIFree()}}>
                    <Image style={{flex: 1, width: 500, height: 500, alignSelf: "center"}} source={require("../assets/images/Final.gif")} />
                </TouchableOpacity>
        );
    }
}

const AmIFreeStack = createStackNavigator({
    AmIFree : AmIFreeScreen,
});

AmIFreeStack.navigationOptions = {
  tabBarLabel: 'Are you Free?',
  tabBarIcon: ({ focused }) => (
    <TabBarIcon
      focused={focused}
      name={'i' === 'ios' ? `ios-link${focused ? '' : '-outline'}` : 'md-link'}
    />
  ),
};


const FriendsListStack = createStackNavigator({
    Friends : FriendsListScreen,
});

FriendsListStack.navigationOptions = {
  tabBarLabel: 'Friends',
  tabBarIcon: ({ focused }) => (
    <TabBarIcon
      focused={focused}
      name={'i' === 'ios' ? `ios-link${focused ? '' : '-outline'}` : 'md-link'}
    />
  ),
};

const SettingsStack = createStackNavigator({
    Settings: SettingsScreen,
});

SettingsStack.navigationOptions = {
    tabBarLabel: 'Edit My Profile',
    tabBarIcon: ({ focused }) => (
        <TabBarIcon
            focused={focused}
            name={'i' === 'ios' ? `ios-options${focused ? '' : '-outline'}` : 'md-options'}
        />
    ),
};

export default createBottomTabNavigator(
    {
        AmIFreeStack,
        FriendsListStack,
        SettingsStack
    }
);

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    animationContainer: {
        // backgroundColor: 'blue',
        // flex: 1,
        // flexDirection: 'column',
        // justifyContent: 'center',
        // alignItems: 'center',
        // height: '100%',
        // width: '100%'
        flex: 1,
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(79, 81, 140, 1.0)'

    }
});
